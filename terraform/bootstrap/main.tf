# Bootstrap : crée le backend distant (S3 + DynamoDB) pour tout le reste de
# l'infrastructure. Ce module reste volontairement en state LOCAL — il ne
# peut pas référencer le backend qu'il est en train de créer (problème classique
# de l'œuf et de la poule). Appliqué une seule fois, puis quasiment jamais
# retouché.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = "eu-west-3"

  default_tags {
    tags = {
      Project   = "ev-powertrain-analytics"
      ManagedBy = "terraform"
      Component = "tfstate-bootstrap"
    }
  }
}

# Suffixe aléatoire : les noms de bucket S3 sont globalement uniques sur tout AWS,
# pas seulement dans ton compte — un nom fixe risquerait un conflit avec un bucket
# existant ailleurs dans le monde.
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "ev-powertrain-analytics-tfstate-${random_id.suffix.hex}"

  # Protection contre un `terraform destroy` accidentel sur l'infra qui
  # protège justement tout le reste de l'infra.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tfstate_lock" {
  name         = "ev-powertrain-analytics-tfstate-lock"
  billing_mode = "PAY_PER_REQUEST" # pas de coût fixe : facturé à la requête, quasi nul ici
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "state_bucket_name" {
  value = aws_s3_bucket.tfstate.bucket
}

output "lock_table_name" {
  value = aws_dynamodb_table.tfstate_lock.name
}
