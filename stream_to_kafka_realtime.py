import argparse
import random
import threading
import time
from datetime import datetime, timedelta, timezone

import numpy as np

from simulator.config import StreamingDemoConfig
from simulator.generator import new_unit_id
from simulator.kafka_producer import TOPIC_BY_SENSOR, build_producer
from simulator.realtime_producer import stream_unit_realtime
from simulator.writer import JsonlWriter


def main():
    parser = argparse.ArgumentParser(
        description="Diffuse des unités vers Kafka en temps réel, plusieurs en parallèle (rythme de ligne de production)"
    )
    parser.add_argument("--num-units", type=int, default=10)
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092")
    parser.add_argument("--manifest-path", type=str, default="data/output/units-manifest.jsonl")
    parser.add_argument(
        "--min-interval", type=float, default=5.0, help="Délai minimum entre le lancement de deux unités (s)"
    )
    parser.add_argument(
        "--max-interval", type=float, default=10.0, help="Délai maximum entre le lancement de deux unités (s)"
    )
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    config = StreamingDemoConfig()
    rng = np.random.default_rng(args.seed)
    producer = build_producer(args.bootstrap_servers)

    manifest_lock = threading.Lock()
    manifest_writer = JsonlWriter(args.manifest_path)

    def run_unit(unit_id, unit_rng):
        manifest_entry = stream_unit_realtime(producer, unit_id, unit_rng, config)
        with manifest_lock:
            manifest_writer.write(manifest_entry)
        print(f"Unité {unit_id} terminée (défectueuse : {manifest_entry['defective']})")

    threads = []
    for _ in range(args.num_units):
        unit_id = new_unit_id()
        # Chaque thread reçoit son propre générateur, dérivé du RNG principal —
        # np.random.Generator n'est pas garanti thread-safe en usage concurrent.
        unit_rng = np.random.default_rng(rng.integers(0, 2**31 - 1))
        thread = threading.Thread(target=run_unit, args=(unit_id, unit_rng))
        thread.start()
        threads.append(thread)
        print(f"Unité {unit_id} lancée")
        time.sleep(random.uniform(args.min_interval, args.max_interval))

    for thread in threads:
        thread.join()

    # Purge : force le watermark à avancer au-delà de la dernière vraie
    # donnée, sinon les sessions des toutes dernières unités restent
    # bloquées indéfiniment (le watermark n'avance que sur réception de
    # nouvelles données, jamais tout seul avec le temps qui passe).
    flush_time = (datetime.now(timezone.utc) + timedelta(seconds=40)).isoformat()
    for sensor_type, topic in TOPIC_BY_SENSOR.items():
        payload = {"unit_id": "flush", "t": 0.0, "value": 0.0, "event_time": flush_time}
        if sensor_type == "current":
            payload["phase"] = "A"
        producer.send(topic, key="flush", value=payload)
    print("Message de purge envoyé (débloque les dernières sessions ouvertes).")

    producer.flush()
    producer.close()
    manifest_writer.close()
    print(f"{args.num_units} unités envoyées en temps réel. Manifeste : {args.manifest_path}")


if __name__ == "__main__":
    main()
