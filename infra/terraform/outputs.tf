output "dynamodb_table_name" {
  description = "DynamoDB sessions table name"
  value       = aws_dynamodb_table.sessions.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB sessions table ARN"
  value       = aws_dynamodb_table.sessions.arn
}

output "reports_bucket_name" {
  description = "S3 bucket for generated reports"
  value       = aws_s3_bucket.reports.id
}

output "reports_bucket_arn" {
  description = "S3 reports bucket ARN"
  value       = aws_s3_bucket.reports.arn
}

output "frontend_bucket_name" {
  description = "S3 bucket for frontend static files"
  value       = aws_s3_bucket.frontend.id
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Cognito App Client ID"
  value       = aws_cognito_user_pool_client.frontend.id
}
