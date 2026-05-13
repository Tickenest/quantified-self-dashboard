output "api_url" {
  description = "HTTP API base URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "frontend_bucket" {
  description = "S3 bucket name for frontend deployment"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_url" {
  description = "S3 static website URL"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "data_bucket" {
  description = "S3 bucket name for Parquet data"
  value       = aws_s3_bucket.data.bucket
}

output "ecr_refresh_url" {
  description = "ECR repository URL for refresh Lambda image"
  value       = aws_ecr_repository.refresh.repository_url
}

output "ecr_query_url" {
  description = "ECR repository URL for query Lambda image"
  value       = aws_ecr_repository.query.repository_url
}

output "dynamodb_table" {
  description = "DynamoDB table name for briefings"
  value       = aws_dynamodb_table.briefings.name
}
