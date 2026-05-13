terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

locals {
  prefix = "qsd-${var.environment}"

  common_tags = {
    Project     = "quantified-self-dashboard"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
