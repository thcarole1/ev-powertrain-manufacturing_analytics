"""Détection en streaming (capteur vibration uniquement pour cette étape).

Chaque session (un test d'unité) se finalise automatiquement dès que plus
aucune mesure n'arrive pour cette unité pendant SESSION_GAP (voir
anomaly/streaming_features.py) — pas de durée de test connue à l'avance,
contrairement à la version batch.

Prochaine étape (non traitée ici) : joindre vibration, température et
courant pour retrouver la classification complète — une jointure
stream-stream à part entière, avec ses propres contraintes de watermark.
"""

import argparse

from consumer.schemas import SENSOR_SCHEMA
from consumer.spark_kafka_reader import build_spark_session, read_sensor_stream
from anomaly.streaming_features import vibration_streaming_features


def main():
    parser = argparse.ArgumentParser(description="Détection streaming sur le capteur vibration")
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092")
    parser.add_argument("--checkpoint-dir", type=str, default="/tmp/spark-checkpoints/streaming-detection")
    args = parser.parse_args()

    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    stream = read_sensor_stream(spark, "sensor-vibration", args.bootstrap_servers, SENSOR_SCHEMA)
    result = vibration_streaming_features(stream)

    query = (
        result.writeStream.format("console")
        .outputMode("append")
        .option("truncate", False)
        .option("checkpointLocation", args.checkpoint_dir)
        .start()
    )
    print("Écoute de sensor-vibration — une ligne apparaît par unité, ~8-15s après la fin de son test.")
    print("Ctrl+C pour arrêter.")
    query.awaitTermination()


if __name__ == "__main__":
    main()
