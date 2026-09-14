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

  # Après un job, l'application reste STARTED — un état que Terraform ne
  # peut pas détruire directement (incident rencontré et documenté dans
  # ADR-006). Ce provisioner l'arrête automatiquement avant la suppression,
  # et attend confirmation de l'arrêt plutôt que de supposer qu'il est
  # instantané. S'exécute en local (poste qui lance terraform destroy),
  # nécessite l'AWS CLI déjà configuré.
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      aws emr-serverless stop-application --application-id ${self.id} --region eu-west-3
      while [ "$(aws emr-serverless get-application --application-id ${self.id} --region eu-west-3 --query 'application.state' --output text)" != "STOPPED" ]; do
        sleep 5
      done
    EOT
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
