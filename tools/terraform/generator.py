"""Terraform Generator — produces IaC from architecture decisions."""

from typing import Any


# Service-to-Terraform mapping templates
SERVICE_TEMPLATES: dict[str, str] = {
    "Amazon ECS": '''
resource "aws_ecs_cluster" "main" {{
  name = "${{local.prefix}}-cluster"

  setting {{
    name  = "containerInsights"
    value = "enabled"
  }}
}}
''',
    "Amazon RDS": '''
resource "aws_db_instance" "main" {{
  identifier           = "${{local.prefix}}-db"
  engine               = "postgres"
  engine_version       = "16"
  instance_class       = "db.t4g.medium"
  allocated_storage    = 20
  storage_encrypted    = true
  multi_az             = {multi_az}
  db_name              = "asa"
  username             = "admin"
  manage_master_user_password = true
  skip_final_snapshot  = true

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
}}
''',
    "Amazon DynamoDB": '''
resource "aws_dynamodb_table" "main" {{
  name         = "${{local.prefix}}-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {{
    name = "pk"
    type = "S"
  }}

  attribute {{
    name = "sk"
    type = "S"
  }}

  point_in_time_recovery {{
    enabled = true
  }}
}}
''',
    "Amazon S3": '''
resource "aws_s3_bucket" "data" {{
  bucket = "${{local.prefix}}-data"
}}

resource "aws_s3_bucket_versioning" "data" {{
  bucket = aws_s3_bucket.data.id
  versioning_configuration {{
    status = "Enabled"
  }}
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {{
  bucket = aws_s3_bucket.data.id
  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "aws:kms"
    }}
  }}
}}
''',
    "Amazon CloudFront": '''
resource "aws_cloudfront_distribution" "main" {{
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {{
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "s3-frontend"

    s3_origin_config {{
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }}
  }}

  default_cache_behavior {{
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {{
      query_string = false
      cookies {{
        forward = "none"
      }}
    }}
  }}

  restrictions {{
    geo_restriction {{
      restriction_type = "none"
    }}
  }}

  viewer_certificate {{
    cloudfront_default_certificate = true
  }}
}}
''',
    "Amazon Cognito": '''
resource "aws_cognito_user_pool" "main" {{
  name = "${{local.prefix}}-users"

  password_policy {{
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }}

  mfa_configuration = "OPTIONAL"

  auto_verified_attributes = ["email"]
}}
''',
    "AWS Lambda": '''
resource "aws_lambda_function" "api" {{
  function_name = "${{local.prefix}}-api"
  runtime       = "python3.12"
  handler       = "handler.lambda_handler"
  timeout       = 30
  memory_size   = 256

  filename         = "lambda.zip"
  source_code_hash = filebase64sha256("lambda.zip")

  role = aws_iam_role.lambda_exec.arn

  environment {{
    variables = {{
      ENVIRONMENT = var.environment
    }}
  }}
}}
''',
    "Amazon API Gateway": '''
resource "aws_apigatewayv2_api" "main" {{
  name          = "${{local.prefix}}-api"
  protocol_type = "HTTP"

  cors_configuration {{
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 300
  }}
}}
''',
    "Amazon ElastiCache": '''
resource "aws_elasticache_cluster" "main" {{
  cluster_id           = "${{local.prefix}}-cache"
  engine               = "redis"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}}
''',
    "Amazon SQS": '''
resource "aws_sqs_queue" "main" {{
  name                      = "${{local.prefix}}-queue"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 345600
  receive_wait_time_seconds = 10

  sqs_managed_sse_enabled = true
}}
''',
}


def generate_terraform(session: dict[str, Any]) -> str:
    """Generate Terraform code based on architecture services."""
    arch = session.get("architecture", {})
    services = arch.get("services", [])
    nfr = arch.get("non_functional", {})
    customer = session.get("customer", {})

    multi_az = "true" if nfr.get("availability_target", "") in ("99.99%", "99.999%") else "false"

    lines = []
    lines.append(f'''# ──────────────────────────────────────────────────────────────
# ASA Generated Terraform — {customer.get("name", "Customer")}
# ──────────────────────────────────────────────────────────────
# This code was auto-generated by ASA (Autonomous Solutions Architect).
# Review and customise before applying to production.
# ──────────────────────────────────────────────────────────────

locals {{
  prefix = "${{var.project_name}}-${{var.environment}}"
}}

variable "project_name" {{
  default = "asa-project"
}}

variable "environment" {{
  default = "dev"
}}

variable "aws_region" {{
  default = "{nfr.get('regions', ['us-east-1'])[0] if nfr.get('regions') else 'us-east-1'}"
}}

provider "aws" {{
  region = var.aws_region
}}
''')

    # Generate resources for each service
    generated_services = set()
    for svc in services:
        service_name = svc.get("service", "")
        if service_name in SERVICE_TEMPLATES and service_name not in generated_services:
            template = SERVICE_TEMPLATES[service_name]
            lines.append(f"# --- {service_name} ---")
            lines.append(f"# Purpose: {svc.get('purpose', '')}")
            lines.append(template.format(multi_az=multi_az))
            generated_services.add(service_name)

    # Services without templates get a comment
    for svc in services:
        service_name = svc.get("service", "")
        if service_name not in SERVICE_TEMPLATES and service_name not in generated_services:
            lines.append(f"# TODO: {service_name} — {svc.get('purpose', '')}")
            lines.append(f"# Justification: {svc.get('justification', '')}")
            lines.append("")
            generated_services.add(service_name)

    return "\n".join(lines)
