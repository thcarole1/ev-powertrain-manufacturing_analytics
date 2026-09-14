# Un dossier dédié dans le bucket existant, pas un nouveau bucket — les
# résultats de requêtes Athena n'ont pas de raison d'être séparés
# physiquement des données qu'ils interrogent.

resource "aws_athena_workgroup" "detection" {
  name = "ev-powertrain-analytics"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = false

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake.bucket}/athena-query-results/"
    }
  }
}

output "athena_workgroup_name" {
  value = aws_athena_workgroup.detection.name
}
