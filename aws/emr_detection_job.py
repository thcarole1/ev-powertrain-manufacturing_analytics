"""Job EMR Serverless — détection d'anomalie en batch sur MSK Serverless réel.

Autonome (logique de anomaly/features.py et anomaly/classify.py réécrite
ici) plutôt que de dépendre d'un mécanisme de packaging (--py-files) non
encore testé dans ce contexte — simplification délibérée pour cette preuve,
pas la pratique recommandée pour un vrai projet à plusieurs fichiers.

Authentification IAM via le connecteur Kafka natif de Spark, configuré
directement (pas de "Glue Connection") — voir ADR-006 pour le contexte.
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

SENSOR_SCHEMA = StructType(
    [
        StructField("unit_id", StringType(), False),
        StructField("t", DoubleType(), False),
        StructField("value", DoubleType(), False),
    ]
)

CURRENT_SCHEMA = StructType(
    [
        StructField("unit_id", StringType(), False),
        StructField("t", DoubleType(), False),
        StructField("phase", StringType(), False),
        StructField("value", DoubleType(), False),
    ]
)

VIBRATION_STD_THRESHOLD = 1.5
TEMPERATURE_RISE_THRESHOLD = 25.0
CURRENT_RATIO_THRESHOLD = 0.85


def read_topic_batch(spark, topic, bootstrap_servers, schema):
    raw = (
        spark.read.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("kafka.security.protocol", "SASL_SSL")
        .option("kafka.sasl.mechanism", "AWS_MSK_IAM")
        .option("kafka.sasl.jaas.config", "software.amazon.msk.auth.iam.IAMLoginModule required;")
        .option("kafka.sasl.client.callback.handler.class", "software.amazon.msk.auth.iam.IAMClientCallbackHandler")
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("endingOffsets", "latest")
        .load()
    )
    return raw.select(F.from_json(F.col("value").cast("string"), schema).alias("data")).select("data.*")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-servers", required=True)
    parser.add_argument("--output-path", required=True, help="s3://bucket/prefix pour écrire les résultats")
    args = parser.parse_args()

    spark = SparkSession.builder.appName("ev-powertrain-emr-detection").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    vibration_df = read_topic_batch(spark, "sensor-vibration", args.bootstrap_servers, SENSOR_SCHEMA)
    temperature_df = read_topic_batch(spark, "sensor-temperature", args.bootstrap_servers, SENSOR_SCHEMA)
    current_df = read_topic_batch(spark, "sensor-current", args.bootstrap_servers, CURRENT_SCHEMA)

    vibration_features = vibration_df.groupBy("unit_id").agg(F.stddev("value").alias("vibration_std"))

    temperature_features = temperature_df.groupBy("unit_id").agg(
        (F.max("value") - F.min("value")).alias("temperature_rise")
    )

    current_features = current_df.groupBy("unit_id").agg(
        F.max(F.when(F.col("phase") == "A", F.abs(F.col("value")))).alias("A"),
        F.max(F.when(F.col("phase") == "B", F.abs(F.col("value")))).alias("B"),
        F.max(F.when(F.col("phase") == "C", F.abs(F.col("value")))).alias("C"),
    ).withColumn("current_imbalance_ratio", F.least("A", "B", "C") / F.greatest("A", "B", "C"))

    joined = vibration_features.join(temperature_features, "unit_id", "outer").join(
        current_features.select("unit_id", "current_imbalance_ratio"), "unit_id", "outer"
    )

    classified = (
        joined.withColumn(
            "predicted_bearing_defect",
            (F.col("vibration_std") > VIBRATION_STD_THRESHOLD)
            | (F.col("temperature_rise") > TEMPERATURE_RISE_THRESHOLD),
        )
        .withColumn(
            "predicted_phase_defect",
            F.col("current_imbalance_ratio") < CURRENT_RATIO_THRESHOLD,
        )
        .withColumn(
            "predicted_defective",
            F.col("predicted_bearing_defect") | F.col("predicted_phase_defect"),
        )
    )

    print("\n=== Détection réalisée sur EMR Serverless, données lues depuis MSK Serverless (IAM) ===")
    classified.orderBy("unit_id").show(100, truncate=False)
    print(f"Total unités détectées : {classified.count()}")
    print(f"Unités défectueuses : {classified.filter(F.col('predicted_defective')).count()}")

    # Parquet : format colonnaire, celui attendu par Athena/Glue Catalog en aval.
    classified.write.mode("overwrite").parquet(args.output_path)
    print(f"Résultats écrits sur {args.output_path}")


if __name__ == "__main__":
    main()
