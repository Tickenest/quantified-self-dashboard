# ---------------------------------------------------------------------------
# HTTP API (API Gateway v2)
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["Content-Type", "Authorization"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = ["*"]
    max_age       = 300
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Query Lambda integration and routes
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_integration" "query" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "query" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.query.id}"
}

resource "aws_lambda_permission" "query_apigw" {
  statement_id  = "AllowAPIGatewayQuery"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Agent Lambda integration and routes
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_integration" "agent" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.agent.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "agent" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /agent"
  target    = "integrations/${aws_apigatewayv2_integration.agent.id}"
}

resource "aws_lambda_permission" "agent_apigw" {
  statement_id  = "AllowAPIGatewayAgent"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Briefings route — frontend fetches latest briefings from DynamoDB via query Lambda
# We add a dedicated GET /briefings route handled by a small addition to query Lambda
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_route" "briefings" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /briefings"
  target    = "integrations/${aws_apigatewayv2_integration.query.id}"
}
