terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket       = "ev-powertrain-analytics-tfstate-fb5f6db7"
    key          = "main/terraform.tfstate"
    region       = "eu-west-3"
    use_lockfile = true
    encrypt      = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-west-3"

  default_tags {
    tags = {
      Project   = "ev-powertrain-analytics"
      ManagedBy = "terraform"
    }
  }
}
