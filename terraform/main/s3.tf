# Premier bucket S3 du projet — anticipe la Phase 4 (Stockage), pas encore
# planifiée formellement, mais nécessaire ici : EMR Serverless exige un
# emplacement S3 pour le script du job et ses journaux.

resource "aws_s3_bucket" "emr_assets" {
  bucket = "ev-powertrain-analytics-emr-${random_id.emr_suffix.hex}"

  tags = { Name = "ev-powertrain-analytics-emr-assets" }
}

resource "random_id" "emr_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_public_access_block" "emr_assets" {
  bucket                  = aws_s3_bucket.emr_assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "emr_assets" {
  bucket = aws_s3_bucket.emr_assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
