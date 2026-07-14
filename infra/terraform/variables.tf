variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "atlas-discovery"
}

variable "cognito_callback_urls" {
  description = "Cognito callback URLs for the frontend"
  type        = list(string)
  default     = ["http://localhost:5173/callback"]
}

variable "frontend_domain" {
  description = "Custom domain for CloudFront distribution (optional)"
  type        = string
  default     = ""
}
