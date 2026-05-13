import boto3
import csv
import io
import logging
import os
import urllib.request
from datetime import datetime

import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ["S3_BUCKET"]
S3_KEY = os.environ.get("S3_KEY", "data/life_log.parquet")
SHEETS_URL = os.environ["SHEETS_URL"]

COLUMNS = ["date", "weight", "exercise", "training", "reading", "gaming", "food"]


def fetch_csv(url: str) -> list[dict]:
    """Fetch CSV from Google Sheets export URL and return as list of dicts."""
    logger.info(f"Fetching CSV from Google Sheets")
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(content))

    # Normalize header names to lowercase
    rows = []
    for row in reader:
        normalized = {k.lower().strip(): v.strip() for k, v in row.items()}
        rows.append(normalized)

    logger.info(f"Fetched {len(rows)} raw rows from sheet")
    return rows


def is_empty_row(row: dict) -> bool:
    """Return True if all fields except date are empty (future placeholder row)."""
    non_date_fields = [v for k, v in row.items() if k != "date"]
    return all(v == "" for v in non_date_fields)


def normalize_date(date_str: str) -> str | None:
    """Normalize date strings like '2026-5-11' to '2026-05-11'."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%-m/%-d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try parsing loosely (handles '2026-5-11' style)
    try:
        parts = date_str.replace("/", "-").split("-")
        if len(parts) == 3:
            y, m, d = parts
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        pass
    logger.warning(f"Could not parse date: {date_str}")
    return None


def clean_rows(rows: list[dict]) -> list[dict]:
    """Filter and clean raw rows."""
    cleaned = []
    skipped_empty = 0
    skipped_bad_date = 0

    for row in rows:
        # Skip future placeholder rows
        if is_empty_row(row):
            skipped_empty += 1
            continue

        # Normalize date
        normalized_date = normalize_date(row.get("date", ""))
        if not normalized_date:
            skipped_bad_date += 1
            continue

        cleaned.append({
            "date":     normalized_date,
            "weight":   float(row["weight"]) if row.get("weight") else None,
            "exercise": row.get("exercise") or None,
            "training": row.get("training") or None,
            "reading":  row.get("reading") or None,
            "gaming":   row.get("gaming") or None,
            "food":     row.get("food") or None,
        })

    logger.info(
        f"Cleaned {len(cleaned)} rows "
        f"(skipped {skipped_empty} empty, {skipped_bad_date} bad date)"
    )
    return cleaned


def write_parquet(rows: list[dict]) -> None:
    """Write cleaned rows to Parquet on S3."""
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )
    logger.info(f"Wrote {len(df)} rows to s3://{S3_BUCKET}/{S3_KEY}")


def lambda_handler(event, context):
    try:
        rows = fetch_csv(SHEETS_URL)
        cleaned = clean_rows(rows)

        if not cleaned:
            logger.warning("No valid rows after cleaning — aborting S3 write")
            return {"statusCode": 200, "body": "No data to write"}

        write_parquet(cleaned)

        return {
            "statusCode": 200,
            "body": f"Successfully wrote {len(cleaned)} rows to S3",
        }

    except Exception as e:
        logger.error(f"Refresh failed: {e}", exc_info=True)
        raise
