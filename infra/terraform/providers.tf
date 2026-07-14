terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — uncomment when ready
  # backend "s3" {
  #   bucket         = "atlas-terraform-state"
  #   key            = "atlas/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "atlas-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "atlas-discovery"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
