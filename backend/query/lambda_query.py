import boto3
import duckdb
import io
import json
import logging
import os
import tempfile
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ["S3_BUCKET"]
S3_KEY = os.environ.get("S3_KEY", "data/life_log.parquet")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "")


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types that json.dumps can't serialize."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

# Valid query types
QUERY_TYPES = {
    # Fitness
    "weight_trend",
    "weight_moving_avg",
    "exercise_entries",
    "exercise_correlation",
    "exercise_streak",
    # Food
    "food_entries",
    # Learning
    "training_entries",
    "books_finished",
    "books_abandoned",
    "book_current",
    # Gaming
    "gaming_entries",
    # General
    "full_window",
    "single_day",
    "date_range",
    # Briefings
    "get_briefing",
}


def load_parquet(conn: duckdb.DuckDBPyConnection, local_path: str) -> None:
    """Register the Parquet file as a DuckDB view."""
    conn.execute(f"CREATE VIEW log AS SELECT * FROM read_parquet('{local_path}')")


def fetch_parquet_locally() -> str:
    """Download Parquet from S3 to a temp file and return the path."""
    s3 = boto3.client("s3")
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    s3.download_fileobj(S3_BUCKET, S3_KEY, tmp)
    tmp.flush()
    return tmp.name


def run_query(conn: duckdb.DuckDBPyConnection, query_type: str, params: dict) -> list[dict]:
    """Dispatch to the appropriate query and return results as list of dicts."""

    start_date = params.get("start_date")
    end_date = params.get("end_date")
    limit = params.get("limit", 90)

    # Build a reusable date filter clause
    def date_filter(alias=""):
        col = f"{alias}.date" if alias else "date"
        parts = []
        if start_date:
            parts.append(f"{col} >= '{start_date}'")
        if end_date:
            parts.append(f"{col} <= '{end_date}'")
        return ("AND " + " AND ".join(parts)) if parts else ""

    if query_type == "weight_trend":
        sql = f"""
            SELECT date, weight
            FROM log
            WHERE weight IS NOT NULL
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "weight_moving_avg":
        sql = f"""
            SELECT date, weight,
                AVG(weight) OVER (
                    ORDER BY date
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) AS moving_avg_7d
            FROM log
            WHERE weight IS NOT NULL
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "exercise_entries":
        sql = f"""
            SELECT date, exercise
            FROM log
            WHERE exercise IS NOT NULL
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "exercise_correlation":
        # Average next-day weight change by exercise type
        # Explodes multi-exercise days so each activity is counted individually
        # Normalizes activity names to collapse variants (e.g. "30 minute walk" -> "walking")
        sql = f"""
            WITH daily AS (
                SELECT date, weight,
                    LEAD(weight) OVER (ORDER BY date) AS next_weight,
                    exercise
                FROM log
                WHERE weight IS NOT NULL AND exercise IS NOT NULL
                {date_filter()}
            ),
            exploded AS (
                SELECT date, next_weight - weight AS weight_change,
                    TRIM(ex) AS raw_activity
                FROM daily,
                UNNEST(string_split(exercise, ',')) AS t(ex)
                WHERE next_weight IS NOT NULL
            ),
            normalized AS (
                SELECT date, weight_change,
                    CASE
                        WHEN LOWER(raw_activity) LIKE '%walk%' THEN 'walking'
                        WHEN LOWER(raw_activity) LIKE '%bike%'
                          OR LOWER(raw_activity) LIKE '%cycling%' THEN 'cycling'
                        WHEN LOWER(raw_activity) LIKE '%run%'
                          OR LOWER(raw_activity) LIKE '%treadmill%' THEN 'running'
                        WHEN LOWER(raw_activity) LIKE '%disc golf%' THEN 'disc golf'
                        WHEN LOWER(raw_activity) LIKE '%ring fit%' THEN 'ring fit'
                        WHEN LOWER(raw_activity) LIKE '%ddr%' THEN 'ddr'
                        WHEN LOWER(raw_activity) LIKE '%weight%'
                          OR LOWER(raw_activity) LIKE '%strength%' THEN 'weight training'
                        WHEN LOWER(raw_activity) LIKE '%swim%' THEN 'swimming'
                        WHEN LOWER(raw_activity) LIKE '%basketball%' THEN 'basketball'
                        WHEN LOWER(raw_activity) LIKE '%soccer%' THEN 'soccer'
                        WHEN LOWER(raw_activity) LIKE '%yoga%' THEN 'yoga'
                        WHEN LOWER(raw_activity) LIKE '%rest%' THEN NULL
                        ELSE LOWER(TRIM(raw_activity))
                    END AS activity
                FROM exploded
            )
            SELECT activity,
                ROUND(AVG(weight_change), 2) AS avg_next_day_change,
                COUNT(*) AS sample_size
            FROM normalized
            WHERE activity IS NOT NULL
            GROUP BY activity
            HAVING COUNT(*) >= 3
            ORDER BY avg_next_day_change ASC
        """

    elif query_type == "exercise_streak":
        # Current consecutive days with any exercise logged (not a rest day)
        sql = f"""
            WITH recent AS (
                SELECT date, exercise,
                    exercise IS NOT NULL
                    AND LOWER(exercise) NOT LIKE '%rest day%' AS exercised
                FROM log
                ORDER BY date DESC
            ),
            streaks AS (
                SELECT date, exercised,
                    SUM(CASE WHEN NOT exercised THEN 1 ELSE 0 END)
                        OVER (ORDER BY date DESC ROWS UNBOUNDED PRECEDING) AS break_count
                FROM recent
            )
            SELECT COUNT(*) AS current_streak
            FROM streaks
            WHERE break_count = 0 AND exercised = true
        """

    elif query_type == "food_entries":
        sql = f"""
            SELECT date, food
            FROM log
            WHERE food IS NOT NULL
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "training_entries":
        sql = f"""
            SELECT date, training
            FROM log
            WHERE training IS NOT NULL
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "books_finished":
        sql = f"""
            SELECT DISTINCT
                REPLACE(reading, ' (finished)', '') AS title,
                date AS finished_date
            FROM log
            WHERE reading LIKE '%(finished)%'
            {date_filter()}
            ORDER BY finished_date DESC
        """

    elif query_type == "books_abandoned":
        # Books that appeared in the log, never finished, and aren't the current book
        sql = f"""
            WITH book_summary AS (
                SELECT
                    REPLACE(reading, ' (finished)', '') AS title,
                    MAX(CASE WHEN reading LIKE '%(finished)%' THEN 1 ELSE 0 END) AS was_finished,
                    MAX(date) AS last_seen
                FROM log
                WHERE reading IS NOT NULL
                GROUP BY REPLACE(reading, ' (finished)', '')
            ),
            current_book AS (
                SELECT REPLACE(reading, ' (finished)', '') AS title
                FROM log
                WHERE reading IS NOT NULL
                ORDER BY date DESC
                LIMIT 1
            )
            SELECT b.title, b.last_seen
            FROM book_summary b
            WHERE b.was_finished = 0
            AND b.title NOT IN (SELECT title FROM current_book)
            ORDER BY b.last_seen DESC
        """

    elif query_type == "book_current":
        sql = f"""
            SELECT REPLACE(reading, ' (finished)', '') AS title, date AS last_logged
            FROM log
            WHERE reading IS NOT NULL
            ORDER BY date DESC
            LIMIT 1
        """

    elif query_type == "gaming_entries":
        sql = f"""
            SELECT date, gaming
            FROM log
            WHERE gaming IS NOT NULL
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "full_window":
        sql = f"""
            SELECT date, weight, exercise, training, reading, gaming, food
            FROM log
            WHERE 1=1
            {date_filter()}
            ORDER BY date DESC
            LIMIT {limit}
        """

    elif query_type == "single_day":
        day = params.get("date")
        if not day:
            raise ValueError("single_day query requires a 'date' parameter")
        sql = f"""
            SELECT date, weight, exercise, training, reading, gaming, food
            FROM log
            WHERE date = '{day}'
            LIMIT 1
        """

    elif query_type == "date_range":
        sql = """
            SELECT MIN(date) AS earliest_date, MAX(date) AS latest_date
            FROM log
        """

    else:
        raise ValueError(f"Unknown query_type: {query_type}")

    logger.info(f"Running query: {query_type}")
    result = conn.execute(sql).fetchdf()
    return json.loads(result.to_json(orient="records", date_format="iso"))


def lambda_handler(event, context):
    try:
        # Support both direct invocation and API Gateway
        if "body" in event and isinstance(event["body"], str):
            body = json.loads(event["body"])
        elif "body" in event and isinstance(event["body"], dict):
            body = event["body"]
        else:
            body = event

        query_type = body.get("query_type")
        if not query_type:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "query_type is required"}),
            }

        if query_type not in QUERY_TYPES:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unknown query_type: {query_type}"}),
            }

        params = body.get("params", {})

        # get_briefing reads from DynamoDB, not Parquet
        if query_type == "get_briefing":
            briefing_type = params.get("briefing_type", "daily_briefing")
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(DYNAMODB_TABLE)
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("briefing_type").eq(briefing_type),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({
                    "query_type": query_type,
                    "count": len(items),
                    "data": items,
                }, cls=DecimalEncoder),
            }

        # All other queries use DuckDB
        local_path = fetch_parquet_locally()
        conn = duckdb.connect()
        load_parquet(conn, local_path)

        results = run_query(conn, query_type, params)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "query_type": query_type,
                "count": len(results),
                "data": results,
            }),
        }

    except ValueError as e:
        logger.warning(f"Bad request: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
        }

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise
