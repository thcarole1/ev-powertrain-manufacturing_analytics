import argparse

from consumer.schemas import CURRENT_SCHEMA, SENSOR_SCHEMA
from consumer.spark_kafka_reader import build_spark_session, read_sensor_stream


def main():
    parser = argparse.ArgumentParser(description="Lit un topic Kafka et affiche les micro-batchs en console")
    parser.add_argument("--topic", type=str, default="sensor-vibration")
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092")
    parser.add_argument("--checkpoint-dir", type=str, default="/tmp/spark-checkpoints/console-consumer")
    parser.add_argument("--trigger-seconds", type=int, default=5)
    args = parser.parse_args()

    schema = CURRENT_SCHEMA if args.topic == "sensor-current" else SENSOR_SCHEMA

    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    stream = read_sensor_stream(spark, args.topic, args.bootstrap_servers, schema)

    query = (
        stream.writeStream.format("console")
        .outputMode("append")
        .option("truncate", False)
        .option("checkpointLocation", args.checkpoint_dir)
        .trigger(processingTime=f"{args.trigger_seconds} seconds")
        .start()
    )
    print(f"Écoute de '{args.topic}' — micro-batch toutes les {args.trigger_seconds}s. Ctrl+C pour arrêter.")
    query.awaitTermination()


if __name__ == "__main__":
    main()
