# ---------------------------------------------------------------------------
# Refresh Lambda — container image
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "refresh" {
  function_name = "${local.prefix}-refresh"
  role          = aws_iam_role.refresh.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.refresh.repository_url}:latest"
  timeout       = var.lambda_timeout
  memory_size   = 512

  environment {
    variables = {
      S3_BUCKET  = aws_s3_bucket.data.bucket
      S3_KEY     = "data/life_log.parquet"
      SHEETS_URL = var.sheets_url
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.refresh]
}

# ---------------------------------------------------------------------------
# Query Lambda — container image
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "query" {
  function_name = "${local.prefix}-query"
  role          = aws_iam_role.query.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.query.repository_url}:latest"
  timeout       = var.lambda_timeout
  memory_size   = 512

  environment {
    variables = {
      S3_BUCKET      = aws_s3_bucket.data.bucket
      S3_KEY         = "data/life_log.parquet"
      DYNAMODB_TABLE = aws_dynamodb_table.briefings.name
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.query]
}

# ---------------------------------------------------------------------------
# Agent Lambda — zip deployment
# ---------------------------------------------------------------------------

data "archive_file" "agent" {
  type        = "zip"
  source_file = "${path.module}/../backend/agent/lambda_agent.py"
  output_path = "${path.module}/agent.zip"
}

resource "aws_lambda_function" "agent" {
  function_name    = "${local.prefix}-agent"
  role             = aws_iam_role.agent.arn
  package_type     = "Zip"
  filename         = data.archive_file.agent.output_path
  source_code_hash = data.archive_file.agent.output_base64sha256
  handler          = "lambda_agent.lambda_handler"
  runtime          = "python3.12"
  timeout          = var.agent_lambda_timeout
  memory_size      = 256

  environment {
    variables = {
      QUERY_LAMBDA_NAME  = aws_lambda_function.query.function_name
      TOKEN_BUDGET_TABLE = aws_dynamodb_table.token_budget.name
      DAILY_TOKEN_BUDGET = "120000"
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.agent]
}

# ---------------------------------------------------------------------------
# Briefing Lambda — zip deployment
# ---------------------------------------------------------------------------

data "archive_file" "briefing" {
  type        = "zip"
  source_file = "${path.module}/../backend/briefing/lambda_briefing.py"
  output_path = "${path.module}/briefing.zip"
}

resource "aws_lambda_function" "briefing" {
  function_name    = "${local.prefix}-briefing"
  role             = aws_iam_role.briefing.arn
  package_type     = "Zip"
  filename         = data.archive_file.briefing.output_path
  source_code_hash = data.archive_file.briefing.output_base64sha256
  handler          = "lambda_briefing.lambda_handler"
  runtime          = "python3.12"
  timeout          = var.agent_lambda_timeout
  memory_size      = 256

  environment {
    variables = {
      AGENT_LAMBDA_NAME = aws_lambda_function.agent.function_name
      DYNAMODB_TABLE    = aws_dynamodb_table.briefings.name
      SES_SENDER        = var.ses_sender
      SES_RECIPIENT     = var.ses_recipient
      DASHBOARD_NAME    = var.dashboard_name
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.briefing]
}

# ---------------------------------------------------------------------------
# CloudWatch log groups
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "refresh" {
  name              = "/aws/lambda/${aws_lambda_function.refresh.function_name}"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "query" {
  name              = "/aws/lambda/${aws_lambda_function.query.function_name}"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "agent" {
  name              = "/aws/lambda/${aws_lambda_function.agent.function_name}"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "briefing" {
  name              = "/aws/lambda/${aws_lambda_function.briefing.function_name}"
  retention_in_days = 30
  tags              = local.common_tags
}
