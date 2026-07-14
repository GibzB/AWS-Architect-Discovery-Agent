# ──────────────────────────────────────────────────────────────
# Atlas Discovery — Main Infrastructure
# ──────────────────────────────────────────────────────────────

locals {
  prefix = "${var.project_name}-${var.environment}"
}

# ──────────────────────────────────────────────────────────────
# DynamoDB — Session Storage
# ──────────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "sessions" {
  name         = "${local.prefix}-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${local.prefix}-sessions"
  }
}

# ──────────────────────────────────────────────────────────────
# S3 — Report Storage
# ──────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "reports" {
  bucket = "${local.prefix}-reports"

  tags = {
    Name = "${local.prefix}-reports"
  }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket = aws_s3_bucket.reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ──────────────────────────────────────────────────────────────
# S3 — Frontend Hosting
# ──────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket = "${local.prefix}-frontend"

  tags = {
    Name = "${local.prefix}-frontend"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ──────────────────────────────────────────────────────────────
# Cognito — Authentication
# ──────────────────────────────────────────────────────────────

resource "aws_cognito_user_pool" "main" {
  name = "${local.prefix}-users"

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  auto_verified_attributes = ["email"]

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }
}

resource "aws_cognito_user_pool_client" "frontend" {
  name         = "${local.prefix}-frontend-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = var.cognito_callback_urls

  supported_identity_providers = ["COGNITO"]
}

# ──────────────────────────────────────────────────────────────
# TODO: API Gateway, Bedrock AgentCore, CloudFront, Lambda
# These will be added in Phase 3 (Infrastructure Sprint)
# ──────────────────────────────────────────────────────────────
