resource "aws_dynamodb_table" "briefings" {
  name         = "${local.prefix}-briefings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "briefing_type"
  range_key    = "timestamp"

  attribute {
    name = "briefing_type"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "token_budget" {
  name         = "${local.prefix}-token-budget"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"

  attribute {
    name = "date"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = local.common_tags
}
