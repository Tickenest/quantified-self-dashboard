# ---------------------------------------------------------------------------
# Refresh rule — daily data pull from Google Sheets
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "refresh" {
  name                = "${local.prefix}-refresh"
  description         = "Daily Google Sheets data refresh"
  schedule_expression = var.refresh_schedule
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "refresh" {
  rule      = aws_cloudwatch_event_rule.refresh.name
  target_id = "refresh-lambda"
  arn       = aws_lambda_function.refresh.arn
}

resource "aws_lambda_permission" "refresh_eventbridge" {
  statement_id  = "AllowEventBridgeRefresh"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.refresh.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.refresh.arn
}

# ---------------------------------------------------------------------------
# Daily briefing rule
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "daily_briefing" {
  name                = "${local.prefix}-daily-briefing"
  description         = "Daily morning briefing"
  schedule_expression = var.daily_briefing_schedule
  is_enabled          = var.enable_briefings
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "daily_briefing" {
  rule      = aws_cloudwatch_event_rule.daily_briefing.name
  target_id = "briefing-lambda-daily"
  arn       = aws_lambda_function.briefing.arn

  input = jsonencode({
    request_type = "daily_briefing"
  })
}

resource "aws_lambda_permission" "daily_briefing_eventbridge" {
  statement_id  = "AllowEventBridgeDailyBriefing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.briefing.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_briefing.arn
}

# ---------------------------------------------------------------------------
# Weekly briefing rule
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "weekly_briefing" {
  name                = "${local.prefix}-weekly-briefing"
  description         = "Weekly Sunday briefing"
  schedule_expression = var.weekly_briefing_schedule
  is_enabled          = var.enable_briefings
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "weekly_briefing" {
  rule      = aws_cloudwatch_event_rule.weekly_briefing.name
  target_id = "briefing-lambda-weekly"
  arn       = aws_lambda_function.briefing.arn

  input = jsonencode({
    request_type = "weekly_briefing"
  })
}

resource "aws_lambda_permission" "weekly_briefing_eventbridge" {
  statement_id  = "AllowEventBridgeWeeklyBriefing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.briefing.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_briefing.arn
}
