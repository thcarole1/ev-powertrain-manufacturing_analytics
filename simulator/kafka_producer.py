"""Diffuse les mesures générées par le simulateur vers Kafka.

Le manifeste de vérité terrain n'est jamais envoyé à Kafka (ADR-002) —
il reste un fichier local, à usage d'évaluation uniquement.
"""

import json

from kafka import KafkaProducer

TOPIC_BY_SENSOR = {
    "temperature": "sensor-temperature",
    "vibration": "sensor-vibration",
    "torque": "sensor-torque",
    "current": "sensor-current",
}


def build_producer(bootstrap_servers="localhost:9092"):
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        key_serializer=lambda k: k.encode("utf-8"),
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )


def stream_unit_records(producer, unit_id, records):
    """Envoie tous les enregistrements d'une unité vers leurs topics respectifs.

    La clé (unit_id) garantit que toutes les mesures d'une même unité
    restent dans la même partition, dans l'ordre — voir le mécanisme
    clé→partition vérifié sur le cluster local.
    """
    for sensor_type, rows in records.items():
        topic = TOPIC_BY_SENSOR[sensor_type]
        for row in rows:
            producer.send(topic, key=unit_id, value=row)
