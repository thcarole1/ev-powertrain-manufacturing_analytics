from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json

from consumer.schemas import SENSOR_SCHEMA

# Coordonnées du connecteur Kafka pour Structured Streaming.
# Doit correspondre exactement à la version de Spark installée (3.5.6,
# alignée sur AWS Glue 5.1) — un écart de version casse le chargement du
# package au démarrage de la session Spark.
KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6"


def build_spark_session(app_name="ev-powertrain-kafka-reader"):
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.jars.packages", KAFKA_PACKAGE)
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def read_sensor_stream(spark, topic, bootstrap_servers="localhost:9092", schema=SENSOR_SCHEMA):
    """Lit un topic Kafka en flux et parse la valeur JSON selon le schéma donné.

    La clé Kafka (unit_id) est conservée séparément de la valeur parsée,
    pour rester visible même si le schéma de la valeur évolue.
    """
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .load()
    )
    return raw.select(
        col("key").cast("string").alias("kafka_key"),
        from_json(col("value").cast("string"), schema).alias("data"),
    ).select("kafka_key", "data.*")
