import boto3
import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_CLIENT = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
LAMBDA_CLIENT = boto3.client("lambda")

MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
QUERY_LAMBDA_NAME = os.environ["QUERY_LAMBDA_NAME"]

# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------
REQUEST_TYPES = {"daily_briefing", "weekly_briefing", "chat", "recommendations"}

# ---------------------------------------------------------------------------
# Default date windows
# ---------------------------------------------------------------------------
def default_window(days: int) -> dict:
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}

def today_str() -> str:
    return datetime.utcnow().date().isoformat()

def yesterday_str() -> str:
    return (datetime.utcnow().date() - timedelta(days=1)).isoformat()

# ---------------------------------------------------------------------------
# Query Lambda tool — shared by all specialists
# ---------------------------------------------------------------------------
def call_query_lambda(query_type: str, params: dict = None) -> dict:
    """Invoke the query Lambda and return parsed results."""
    payload = {"query_type": query_type, "params": params or {}}
    response = LAMBDA_CLIENT.invoke(
        FunctionName=QUERY_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    body = json.loads(response["Payload"].read())
    if isinstance(body.get("body"), str):
        return json.loads(body["body"])
    return body


# ---------------------------------------------------------------------------
# Specialist agent runner — generic Claude invocation with tool use
# ---------------------------------------------------------------------------
def run_specialist(
    system_prompt: str,
    task: str,
    allowed_query_types: list[str],
    specialist_name: str,
) -> str:
    """
    Run a specialist agent with tool access limited to its domain query types.
    Returns the specialist's findings as a prose string.
    """

    # Tool definition for this specialist
    query_tool = {
        "name": "query_data",
        "description": (
            "Query the user's life log database. "
            f"Allowed query types for this agent: {', '.join(allowed_query_types)}. "
            "Pass start_date and end_date (YYYY-MM-DD) in params to filter by date range. "
            "Pass limit in params to control result count (default 90)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": allowed_query_types,
                    "description": "The type of data to retrieve.",
                },
                "params": {
                    "type": "object",
                    "description": "Optional parameters: start_date, end_date, limit, date.",
                    "properties": {
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "limit": {"type": "integer"},
                        "date": {"type": "string"},
                    },
                },
            },
            "required": ["query_type"],
        },
    }

    messages = [{"role": "user", "content": task}]

    # Agentic loop — allow multiple tool calls
    for _ in range(10):  # max iterations
        response = BEDROCK_CLIENT.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "system": system_prompt,
                "messages": messages,
                "tools": [query_tool],
                "max_tokens": 2048,
            }),
        )
        result = json.loads(response["body"].read())
        content = result["content"]
        stop_reason = result["stop_reason"]

        # Append assistant response to messages
        messages.append({"role": "assistant", "content": content})

        if stop_reason == "end_turn":
            # Extract final text response
            text_blocks = [b["text"] for b in content if b["type"] == "text"]
            return "\n".join(text_blocks).strip()

        if stop_reason == "tool_use":
            # Process all tool calls in this response
            tool_results = []
            for block in content:
                if block["type"] == "tool_use":
                    tool_input = block["input"]
                    query_type = tool_input.get("query_type")
                    params = tool_input.get("params", {})

                    # Enforce allowed query types
                    if query_type not in allowed_query_types:
                        tool_result = {"error": f"Query type {query_type} not allowed for this agent"}
                    else:
                        try:
                            tool_result = call_query_lambda(query_type, params)
                        except Exception as e:
                            tool_result = {"error": str(e)}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": json.dumps(tool_result),
                    })

            messages.append({"role": "user", "content": tool_results})

    logger.warning(f"{specialist_name} hit max iterations")
    return f"[{specialist_name} could not complete analysis within iteration limit]"


# ---------------------------------------------------------------------------
# Specialist agents
# ---------------------------------------------------------------------------

FITNESS_SYSTEM_PROMPT = """You are the Fitness Agent, a specialist in analyzing personal health and exercise data.

Your role is to:
- Analyze weight trends, identifying direction, plateaus, and notable changes
- Evaluate exercise consistency, frequency, streaks, and variety
- Identify correlations between exercise types and next-day weight changes
- Notice patterns worth highlighting (e.g. weight increasing despite regular exercise, long streaks, rest day clusters)
- When asked for recommendations, suggest specific exercises the user hasn't tried or hasn't done recently, based on their existing activity patterns

Be analytical and specific. Reference actual numbers and dates when relevant.
Write in plain conversational prose. Do not use bullet points or headers.
Focus on what is genuinely interesting or actionable, not just a summary of the data."""

FOOD_SYSTEM_PROMPT = """You are the Food Agent, a specialist in analyzing personal dietary patterns.

Your role is to:
- Assess daily food entries qualitatively (healthy, mixed, or indulgent)
- Identify patterns in eating habits (weekday vs weekend, before/after exercise, recurring foods)
- Notice trends over time (improving, declining, or stable dietary quality)
- Flag unusually heavy or unusually light eating days
- When asked for recommendations, suggest meal ideas that align with foods the user seems to enjoy, 
  nudging toward healthier options where appropriate. Be specific and practical.

The food log is descriptive, not quantified — reason qualitatively about food quality.
Write in plain conversational prose. Do not use bullet points or headers.
Be honest but not preachy about dietary patterns."""

LEARNING_SYSTEM_PROMPT = """You are the Learning Agent, a specialist in analyzing personal reading and training data.

Your role is to:
- Track books currently being read, recently finished, and abandoned
- Identify reading pace and consistency
- Analyze training course activity and progression
- Notice patterns in learning habits (consistency, topic areas, pace)
- When asked for recommendations, suggest books similar to ones the user has enjoyed 
  (based on genre, themes, authors) and training topics that would logically follow 
  from their current progression. Draw on your knowledge of books and learning paths.

Write in plain conversational prose. Do not use bullet points or headers.
Be specific about titles and topics."""

GAMING_SYSTEM_PROMPT = """You are the Gaming Agent, a specialist in analyzing personal gaming habits.

Your role is to:
- Identify which games the user has been playing recently
- Analyze gaming frequency, variety, and session patterns
- Notice trends (playing more or less, trying new games, returning to favorites)
- When asked for recommendations, suggest games the user might enjoy based on 
  what they've been playing, drawing on your knowledge of games and genres.

Note: the user does not mark games as finished in their log. Do not infer completion.
Write in plain conversational prose. Do not use bullet points or headers.
Keep the tone light — this is leisure time."""

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent for a personal life dashboard.

You receive findings from specialist agents (Fitness, Food, Learning, Gaming) and synthesize 
them into a coherent, useful response for the user.

Your role varies by request type:
- Daily briefing: A concise morning summary of yesterday. Warm but efficient. 2-3 paragraphs.
- Weekly briefing: A fuller retrospective of the past week. Conversational and reflective. 3-5 paragraphs.
- Chat: Answer the user's specific question directly, drawing on whichever specialist findings are relevant.
- Recommendations: Offer specific, actionable suggestions across whichever domains were consulted.

Write in plain conversational prose. Do not use bullet points or headers.
Be genuine and specific — reference actual data points, not vague generalities.
Do not be sycophantic. Do not repeat yourself.
The user is an adult who appreciates directness."""


def run_fitness_agent(task: str) -> str:
    return run_specialist(
        system_prompt=FITNESS_SYSTEM_PROMPT,
        task=task,
        allowed_query_types=[
            "weight_trend",
            "weight_moving_avg",
            "exercise_entries",
            "exercise_correlation",
            "exercise_streak",
        ],
        specialist_name="FitnessAgent",
    )


def run_food_agent(task: str) -> str:
    return run_specialist(
        system_prompt=FOOD_SYSTEM_PROMPT,
        task=task,
        allowed_query_types=["food_entries"],
        specialist_name="FoodAgent",
    )


def run_learning_agent(task: str) -> str:
    return run_specialist(
        system_prompt=LEARNING_SYSTEM_PROMPT,
        task=task,
        allowed_query_types=[
            "training_entries",
            "books_finished",
            "books_abandoned",
            "book_current",
        ],
        specialist_name="LearningAgent",
    )


def run_gaming_agent(task: str) -> str:
    return run_specialist(
        system_prompt=GAMING_SYSTEM_PROMPT,
        task=task,
        allowed_query_types=["gaming_entries"],
        specialist_name="GamingAgent",
    )


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

def run_supervisor(request_type: str, message: str, findings: dict) -> str:
    """
    Synthesize specialist findings into a final response.
    findings: dict of {agent_name: findings_string}
    """
    findings_text = "\n\n".join(
        f"=== {name} ===\n{text}"
        for name, text in findings.items()
        if text
    )

    user_content = f"""Request type: {request_type}
{"User message: " + message if message else ""}

Specialist findings:
{findings_text}

Please synthesize these findings into a response appropriate for the request type."""

    response = BEDROCK_CLIENT.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "system": SUPERVISOR_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 2048,
        }),
    )
    result = json.loads(response["body"].read())
    text_blocks = [b["text"] for b in result["content"] if b["type"] == "text"]
    return "\n".join(text_blocks).strip()


# ---------------------------------------------------------------------------
# Orchestration — decide which agents to consult and with what task
# ---------------------------------------------------------------------------

def build_specialist_tasks(request_type: str, message: str) -> dict:
    """
    Return a dict of {agent_name: task_string} for the agents to consult.
    For briefings, always consult all four.
    For chat/recommendations, route based on message content.
    """
    yesterday = yesterday_str()
    window_30 = default_window(30)
    window_7 = default_window(7)

    if request_type == "daily_briefing":
        return {
            "Fitness": (
                f"Analyze the user's fitness data for yesterday ({yesterday}) and recent trends. "
                f"Fetch yesterday's weight and exercise entry, plus weight trend and exercise entries "
                f"for the past 30 days. Provide a concise summary of yesterday and any notable trends."
            ),
            "Food": (
                f"Analyze the user's food log for yesterday ({yesterday}) and recent patterns. "
                f"Fetch food entries for the past 14 days. Assess yesterday's eating quality "
                f"and any patterns worth noting."
            ),
            "Learning": (
                f"Summarize the user's learning activity for yesterday ({yesterday}). "
                f"Fetch training entries and current book for recent context. "
                f"Note what they worked on and what they're reading."
            ),
            "Gaming": (
                f"Summarize the user's gaming activity for yesterday ({yesterday}). "
                f"Fetch gaming entries for the past 7 days for context."
            ),
        }

    elif request_type == "weekly_briefing":
        start = window_7["start_date"]
        end = window_7["end_date"]
        return {
            "Fitness": (
                f"Analyze the user's fitness data for the past week ({start} to {end}). "
                f"Fetch weight trend, moving average, exercise entries, and exercise streak. "
                f"Also fetch exercise correlation data for context. "
                f"Provide a thorough weekly fitness summary including trends and patterns."
            ),
            "Food": (
                f"Analyze the user's food log for the past week ({start} to {end}). "
                f"Fetch food entries for the past 30 days for trend context. "
                f"Provide a weekly dietary assessment — overall quality, patterns, notable days."
            ),
            "Learning": (
                f"Summarize the user's learning activity for the past week ({start} to {end}). "
                f"Fetch training entries, current book, and books finished. "
                f"Note progress, consistency, and anything completed."
            ),
            "Gaming": (
                f"Summarize the user's gaming activity for the past week ({start} to {end}). "
                f"Fetch gaming entries for the past 30 days for context on variety and frequency."
            ),
        }

    elif request_type == "recommendations":
        # Always consult all agents for recommendations
        return {
            "Fitness": (
                f"Based on the user's exercise history over the past 90 days, "
                f"suggest exercises or activities they might enjoy or benefit from trying. "
                f"Fetch exercise entries for the past 90 days. "
                f"Be specific — reference what they've been doing and what might complement it."
            ),
            "Food": (
                f"Based on the user's food log over the past 90 days, "
                f"suggest specific meal ideas they might enjoy. "
                f"Fetch food entries for the past 90 days. "
                f"Draw on foods they seem to like and nudge toward healthier options where natural."
            ),
            "Learning": (
                f"Based on the user's reading history and training progression, "
                f"recommend books and training topics to explore next. "
                f"Fetch books finished, current book, and training entries for the past 90 days. "
                f"Be specific with titles and topics."
            ),
            "Gaming": (
                f"Based on the user's gaming history over the past 90 days, "
                f"suggest games they might enjoy. "
                f"Fetch gaming entries for the past 90 days. "
                f"Reference what they've been playing and suggest something in a similar vein."
            ),
        }

    else:  # chat
        # Route based on message keywords — consult relevant agents only
        msg_lower = message.lower()

        fitness_keywords = {"weight", "exercise", "workout", "walk", "run", "bike", "fitness",
                           "health", "pounds", "lbs", "streak", "active", "sport", "disc golf",
                           "ddr", "ring fit", "basketball", "soccer"}
        food_keywords = {"eat", "food", "meal", "diet", "lunch", "dinner", "breakfast",
                        "snack", "nutrition", "hungry", "cook", "recipe", "drink"}
        learning_keywords = {"book", "read", "reading", "train", "training", "learn", "course",
                            "study", "udemy", "chapter", "finish", "studying"}
        gaming_keywords = {"game", "gaming", "play", "playing", "video", "console",
                          "controller", "steam", "switch"}

        words = set(msg_lower.split())
        tasks = {}

        if words & fitness_keywords:
            tasks["Fitness"] = (
                f"The user asked: '{message}'. "
                f"Fetch relevant fitness data to answer this question. "
                f"Use your judgment about which query types and date ranges are most relevant."
            )
        if words & food_keywords:
            tasks["Food"] = (
                f"The user asked: '{message}'. "
                f"Fetch relevant food data to answer this question. "
                f"Use your judgment about which date range is most relevant."
            )
        if words & learning_keywords:
            tasks["Learning"] = (
                f"The user asked: '{message}'. "
                f"Fetch relevant learning and reading data to answer this question."
            )
        if words & gaming_keywords:
            tasks["Gaming"] = (
                f"The user asked: '{message}'. "
                f"Fetch relevant gaming data to answer this question."
            )

        # If no keywords matched, consult all agents
        if not tasks:
            window = default_window(30)
            for agent in ["Fitness", "Food", "Learning", "Gaming"]:
                tasks[agent] = (
                    f"The user asked: '{message}'. "
                    f"Fetch data from the past 30 days that might be relevant to this question "
                    f"and provide any findings that could help answer it."
                )

        return tasks


AGENT_RUNNERS = {
    "Fitness": run_fitness_agent,
    "Food": run_food_agent,
    "Learning": run_learning_agent,
    "Gaming": run_gaming_agent,
}


def orchestrate(request_type: str, message: str = "") -> str:
    """Main orchestration: consult specialists in parallel, synthesize with supervisor."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = build_specialist_tasks(request_type, message)
    logger.info(f"Consulting agents in parallel: {list(tasks.keys())}")

    findings = {}

    def run_agent(agent_name, task):
        logger.info(f"Running {agent_name} agent")
        runner = AGENT_RUNNERS[agent_name]
        result = runner(task)
        logger.info(f"{agent_name} agent complete")
        return agent_name, result

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_agent, agent_name, task): agent_name
            for agent_name, task in tasks.items()
        }
        for future in as_completed(futures):
            agent_name, result = future.result()
            findings[agent_name] = result

    # Preserve consistent ordering for supervisor
    ordered_findings = {
        name: findings[name]
        for name in ["Fitness", "Food", "Learning", "Gaming"]
        if name in findings
    }

    logger.info("Running supervisor synthesis")
    return run_supervisor(request_type, message, ordered_findings)


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    try:
        # Support API Gateway and direct invocation
        if "body" in event and isinstance(event["body"], str):
            body = json.loads(event["body"])
        elif "body" in event and isinstance(event["body"], dict):
            body = event["body"]
        else:
            body = event

        request_type = body.get("request_type")
        message = body.get("message", "")

        if not request_type:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "request_type is required"}),
            }

        if request_type not in REQUEST_TYPES:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unknown request_type: {request_type}"}),
            }

        response_text = orchestrate(request_type, message)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "request_type": request_type,
                "response": response_text,
            }),
        }

    except Exception as e:
        logger.error(f"Agent Lambda failed: {e}", exc_info=True)
        raise
