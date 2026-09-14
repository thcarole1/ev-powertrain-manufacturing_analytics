# Table définie explicitement (schéma déjà connu) plutôt qu'un Glue Crawler —
# plus simple, gratuit, pas de service supplémentaire à faire tourner.

resource "aws_glue_catalog_database" "detection" {
  name = "ev_powertrain_analytics"
}

resource "aws_glue_catalog_table" "detection_results" {
  name          = "detection_results"
  database_name = aws_glue_catalog_database.detection.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification" = "parquet"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake.bucket}/detection-results/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "unit_id"
      type = "string"
    }
    columns {
      name = "vibration_std"
      type = "double"
    }
    columns {
      name = "temperature_rise"
      type = "double"
    }
    columns {
      name = "current_imbalance_ratio"
      type = "double"
    }
    columns {
      name = "predicted_bearing_defect"
      type = "boolean"
    }
    columns {
      name = "predicted_phase_defect"
      type = "boolean"
    }
    columns {
      name = "predicted_defective"
      type = "boolean"
    }
  }
}

output "glue_database_name" {
  value = aws_glue_catalog_database.detection.name
}

output "glue_table_name" {
  value = aws_glue_catalog_table.detection_results.name
}
