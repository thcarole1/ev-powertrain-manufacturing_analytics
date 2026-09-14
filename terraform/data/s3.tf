# Module séparé de terraform/main : ce bucket contient les résultats de
# détection (Parquet) et doit survivre à la destruction de l'infra éphémère
# (MSK, bastion, EMR Serverless) entre les sessions — coût négligeable au
# repos, contrairement à MSK/EMR.

resource "aws_s3_bucket" "data_lake" {
  bucket = "ev-powertrain-analytics-datalake-${random_id.datalake_suffix.hex}"

  tags = { Name = "ev-powertrain-analytics-datalake" }
}

resource "random_id" "datalake_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
