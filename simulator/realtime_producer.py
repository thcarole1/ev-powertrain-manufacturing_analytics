"""Diffuse les mesures d'une unité en respectant un rythme temps réel.

Les valeurs sont calculées d'un coup (vectorisé, via generate_unit), puis
regroupées par seconde et envoyées avec une pause réelle entre chaque
seconde. event_time est l'horloge murale au moment réel de l'envoi — pas
une valeur précalculée — pour que le watermark Spark reflète un rythme
honnête, sans faire bondir artificiellement l'horloge en avance.
"""

import time
from datetime import datetime, timezone

from simulator.generator import generate_unit
from simulator.kafka_producer import TOPIC_BY_SENSOR

TEST_DURATION_SECONDS = 30


def _bucket_records_by_second(records):
    """Regroupe les enregistrements de toutes les sondes par seconde (0 à 29)."""
    buckets = {i: [] for i in range(TEST_DURATION_SECONDS)}
    for sensor_type, rows in records.items():
        topic = TOPIC_BY_SENSOR[sensor_type]
        for row in rows:
            bucket = min(int(row["t"]), TEST_DURATION_SECONDS - 1)
            buckets[bucket].append((topic, row))
    return buckets


def stream_unit_realtime(producer, unit_id, rng, config):
    """Envoie toutes les mesures d'une unité, étalées sur ~30 secondes réelles.

    Retourne l'entrée de manifeste correspondante, à écrire séparément
    (ADR-002 : jamais mélangée aux mesures envoyées à Kafka).
    """
    records, manifest_entry = generate_unit(unit_id, rng, config)
    buckets = _bucket_records_by_second(records)

    for second in range(TEST_DURATION_SECONDS):
        now = datetime.now(timezone.utc).isoformat()
        for topic, row in buckets[second]:
            enriched = dict(row)
            enriched["event_time"] = now
            producer.send(topic, key=unit_id, value=enriched)
        time.sleep(1)

    return manifest_entry
