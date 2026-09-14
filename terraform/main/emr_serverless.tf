# L'application EMR Serverless ne coûte rien tant qu'aucun job ne tourne
# (facturation uniquement au calcul réellement consommé pendant un job) —
# pas besoin de la détruire entre deux sessions, contrairement à MSK.

resource "aws_emrserverless_application" "detection" {
  name          = "ev-powertrain-analytics-detection"
  release_label = "emr-7.13.0" # Spark 3.5.6 — identique à la version locale/bastion
  type          = "SPARK"

  network_configuration {
    subnet_ids         = [for s in data.aws_subnet.default_per_az : s.id]
    security_group_ids = [aws_security_group.emr_serverless.id]
  }

  tags = { Name = "ev-powertrain-analytics-emr-serverless" }
}

output "emr_application_id" {
  value = aws_emrserverless_application.detection.id
}

output "emr_job_role_arn" {
  value = aws_iam_role.emr_serverless_job.arn
}

output "emr_assets_bucket" {
  value = aws_s3_bucket.emr_assets.bucket
}
