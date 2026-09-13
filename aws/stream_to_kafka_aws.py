"""Diffuse des unités simulées vers MSK Serverless, en mode batch séquentiel.

Volontairement PAS en mode temps réel/multi-thread (stream_to_kafka_realtime.py) :
évite complètement le risque de fragmentation par contention du GIL déjà
rencontré en local — une seule unité à la fois, aucune concurrence.

À exécuter depuis le dossier aws/ du repo cloné sur le bastion :
    cd aws && python3 stream_to_kafka_aws.py --bootstrap-servers <adresse> --num-units 5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # racine du repo, pour importer `simulator`

import numpy as np

from kafka_producer_iam import build_iam_producer
from simulator.config import SimulationConfig
from simulator.generator import generate_unit, new_unit_id
from simulator.kafka_producer import TOPIC_BY_SENSOR
from simulator.writer import JsonlWriter


def stream_unit(producer, unit_id, records):
    for sensor_type, rows in records.items():
        topic = TOPIC_BY_SENSOR[sensor_type]
        for row in rows:
            producer.send(topic, key=unit_id, value=row)


def main():
    parser = argparse.ArgumentParser(description="Diffuse des unités vers MSK Serverless (batch séquentiel)")
    parser.add_argument("--bootstrap-servers", type=str, required=True)
    parser.add_argument("--num-units", type=int, default=5)
    parser.add_argument("--manifest-path", type=str, default="units-manifest-aws.jsonl")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    config = SimulationConfig()
    rng = np.random.default_rng(args.seed)
    producer = build_iam_producer(args.bootstrap_servers)
    manifest_writer = JsonlWriter(args.manifest_path)

    for _ in range(args.num_units):
        unit_id = new_unit_id()
        records, manifest_entry = generate_unit(unit_id, rng, config)
        stream_unit(producer, unit_id, records)
        manifest_writer.write(manifest_entry)
        print(f"Unité {unit_id} envoyée (défectueuse : {manifest_entry['defective']})")

    # flush()/close() bornés — leçon retenue de l'épisode du blocage local.
    producer.flush(timeout=120)
    producer.close(timeout=30)
    manifest_writer.close()
    print(f"{args.num_units} unités envoyées vers MSK Serverless. Manifeste : {args.manifest_path}")


if __name__ == "__main__":
    main()
