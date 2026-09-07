import argparse
import csv

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from anomaly.classify import classify_units
from anomaly.evaluation import evaluate_against_manifest
from anomaly.features import current_features, temperature_features, vibration_features
from consumer.schemas import CURRENT_SCHEMA, SENSOR_SCHEMA

KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6"


def read_topic_batch(spark, topic, bootstrap_servers, schema):
    """Lecture statique (spark.read, pas spark.readStream) — une photo figée du topic."""
    raw = (
        spark.read.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("endingOffsets", "latest")
        .load()
    )
    return raw.select(F.from_json(F.col("value").cast("string"), schema).alias("data")).select("data.*")


def main():
    parser = argparse.ArgumentParser(description="Détection d'anomalie en batch sur les données déjà dans Kafka")
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092")
    parser.add_argument("--manifest-path", type=str, default="data/output/units-manifest.jsonl")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("ev-powertrain-batch-detection")
        .config("spark.jars.packages", KAFKA_PACKAGE)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    vibration_df = read_topic_batch(spark, "sensor-vibration", args.bootstrap_servers, SENSOR_SCHEMA)
    temperature_df = read_topic_batch(spark, "sensor-temperature", args.bootstrap_servers, SENSOR_SCHEMA)
    current_df = read_topic_batch(spark, "sensor-current", args.bootstrap_servers, CURRENT_SCHEMA)

    predictions = classify_units(
        vibration_features(vibration_df),
        temperature_features(temperature_df),
        current_features(current_df),
    )

    manifest_df = spark.read.json(args.manifest_path)

    results = evaluate_against_manifest(predictions, manifest_df)
    print("\nRésultats de détection (comparés au manifeste, jamais utilisés pour prédire) :")
    for key, value in results.items():
        print(f"  {key}: {value}")

    comparison = (
        predictions.join(manifest_df.select("unit_id", "defective", "defect_type"), "unit_id", "inner")
        .withColumn("correct", F.col("predicted_defective") == F.col("defective"))
        .select(
            "unit_id",
            "vibration_std",
            "temperature_rise",
            "current_imbalance_ratio",
            "predicted_defective",
            F.col("defective").alias("actual_defective"),
            "defect_type",
            "correct",
        )
        .orderBy("unit_id")
    )

    print("\nDétail par unité — prédiction et vérité terrain côte à côte :")
    comparison.show(100, truncate=False)

    comparison_path = "data/output/detection_results.csv"
    with open(comparison_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(comparison.columns)
        for row in comparison.collect():
            writer.writerow(row)
    print(f"Comparaison complète exportée dans {comparison_path}")


if __name__ == "__main__":
    main()
