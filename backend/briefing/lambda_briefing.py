import boto3
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LAMBDA_CLIENT = boto3.client("lambda")
DYNAMODB = boto3.resource("dynamodb")
SES_CLIENT = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))

AGENT_LAMBDA_NAME = os.environ["AGENT_LAMBDA_NAME"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
SES_SENDER = os.environ["SES_SENDER"]
SES_RECIPIENT = os.environ["SES_RECIPIENT"]
DASHBOARD_NAME = os.environ.get("DASHBOARD_NAME", "Quantified Self Dashboard")


# ---------------------------------------------------------------------------
# Call agent Lambda
# ---------------------------------------------------------------------------

def get_briefing(briefing_type: str) -> str:
    """Invoke the agent Lambda and return the briefing text."""
    logger.info(f"Requesting {briefing_type} from agent Lambda")
    response = LAMBDA_CLIENT.invoke(
        FunctionName=AGENT_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"request_type": briefing_type}),
    )
    body = json.loads(response["Payload"].read())
    if isinstance(body.get("body"), str):
        parsed = json.loads(body["body"])
    else:
        parsed = body

    if "error" in parsed:
        raise RuntimeError(f"Agent Lambda returned error: {parsed['error']}")

    return parsed["response"]


# ---------------------------------------------------------------------------
# Store in DynamoDB
# ---------------------------------------------------------------------------

def store_briefing(briefing_type: str, text: str, timestamp: str) -> None:
    """Write the briefing to DynamoDB for display in the dashboard."""
    table = DYNAMODB.Table(DYNAMODB_TABLE)
    table.put_item(Item={
        "briefing_type": briefing_type,       # partition key: "daily_briefing" | "weekly_briefing"
        "timestamp": timestamp,                # sort key: ISO 8601
        "text": text,
        "ttl": int(datetime.now(timezone.utc).timestamp()) + (90 * 24 * 60 * 60),  # 90 day TTL
    })
    logger.info(f"Stored {briefing_type} in DynamoDB at {timestamp}")


# ---------------------------------------------------------------------------
# Send via SES
# ---------------------------------------------------------------------------

def build_subject(briefing_type: str, timestamp: str) -> str:
    date_str = timestamp[:10]  # YYYY-MM-DD
    if briefing_type == "daily_briefing":
        return f"{DASHBOARD_NAME} — Daily Briefing ({date_str})"
    elif briefing_type == "weekly_briefing":
        return f"{DASHBOARD_NAME} — Weekly Briefing ({date_str})"
    return f"{DASHBOARD_NAME} — Briefing ({date_str})"


def send_email(subject: str, body: str) -> None:
    """Send the briefing as a plain text email via SES."""
    SES_CLIENT.send_email(
        Source=SES_SENDER,
        Destination={"ToAddresses": [SES_RECIPIENT]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        },
    )
    logger.info(f"Sent email to {SES_RECIPIENT}")


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """
    Triggered by EventBridge on a schedule.
    EventBridge rule passes request_type in the event detail:
      { "request_type": "daily_briefing" } or { "request_type": "weekly_briefing" }
    """
    try:
        # EventBridge passes detail in event["detail"]
        briefing_type = (
            event.get("detail", {}).get("request_type")
            or event.get("request_type")
        )

        if briefing_type not in ("daily_briefing", "weekly_briefing"):
            raise ValueError(
                f"Invalid or missing request_type in event: {briefing_type}. "
                "Expected 'daily_briefing' or 'weekly_briefing'."
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(f"Starting {briefing_type} at {timestamp}")

        # Get briefing from agent Lambda
        briefing_text = get_briefing(briefing_type)

        # Store in DynamoDB
        store_briefing(briefing_type, briefing_text, timestamp)

        # Send via SES
        subject = build_subject(briefing_type, timestamp)
        send_email(subject, briefing_text)

        logger.info(f"{briefing_type} delivered successfully")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "briefing_type": briefing_type,
                "timestamp": timestamp,
                "status": "delivered",
            }),
        }

    except Exception as e:
        logger.error(f"Briefing Lambda failed: {e}", exc_info=True)
        raise
