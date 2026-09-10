"""Lance 3 requêtes streaming indépendantes (une par capteur), chacune écrit
ses résultats finalisés dans un fichier JSON Lines.

Remplace la jointure stream-stream (abandonnée après blocage non résolu —
voir ADR-003) par un découplage : streaming pour chaque capteur seul
(mécanisme déjà validé), jointure en batch classique séparée
(detect_anomalies_from_streaming_files.py).
"""

import argparse
import os

from anomaly.streaming_features import (
    current_streaming_features,
    temperature_streaming_features,
    vibration_streaming_features,
)
from consumer.schemas import CURRENT_SCHEMA, SENSOR_SCHEMA
from consumer.spark_kafka_reader import build_spark_session, read_sensor_stream
from consumer.streaming_sink import append_batch_to_jsonl


def main():
    parser = argparse.ArgumentParser(description="Écrit les résultats streaming de chaque capteur dans un fichier")
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092")
    parser.add_argument("--output-dir", type=str, default="data/output/streaming")
    parser.add_argument("--checkpoint-dir", type=str, default="/tmp/spark-checkpoints/streaming-sinks")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    sensor_names = ("vibration", "temperature", "current")
    for name in sensor_names:
        open(os.path.join(args.output_dir, f"{name}.jsonl"), "w").close()

    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    vibration_result = vibration_streaming_features(
        read_sensor_stream(spark, "sensor-vibration", args.bootstrap_servers, SENSOR_SCHEMA)
    ).drop("session_window")
    temperature_result = temperature_streaming_features(
        read_sensor_stream(spark, "sensor-temperature", args.bootstrap_servers, SENSOR_SCHEMA)
    ).drop("session_window")
    current_result = current_streaming_features(
        read_sensor_stream(spark, "sensor-current", args.bootstrap_servers, CURRENT_SCHEMA)
    ).drop("session_window")
    # A, B, C conservées volontairement (pas juste le ratio) : si le
    # problème persiste, elles permettent de voir directement quelle phase
    # s'effondre, plutôt que de deviner à partir du seul ratio agrégé.

    for result, name in [
        (vibration_result, "vibration"),
        (temperature_result, "temperature"),
        (current_result, "current"),
    ]:
        path = os.path.join(args.output_dir, f"{name}.jsonl")
        (
            result.writeStream.foreachBatch(append_batch_to_jsonl(path))
            .outputMode("append")
            .option("checkpointLocation", os.path.join(args.checkpoint_dir, name))
            .trigger(processingTime="5 seconds")
            .start()
        )

    print(f"3 requêtes streaming actives, écriture dans {args.output_dir}/")
    print("Ctrl+C pour arrêter.")
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
