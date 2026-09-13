"""Crée les 4 topics réels du projet sur MSK Serverless.

replication_factor=3 : valeur imposée par kafka-python 2.0.2 côté client
(refuse -1), sans effet réel côté serveur — MSK Serverless gère la
réplication lui-même, quelle que soit la valeur envoyée.
"""

import sys

from kafka import KafkaAdminClient
from kafka.admin import NewTopic

from kafka_producer_iam import MSKTokenProvider

BOOTSTRAP_SERVERS = "A_REMPLACER"  # sortie Terraform : msk_bootstrap_brokers
TOPICS = ["sensor-temperature", "sensor-vibration", "sensor-torque", "sensor-current"]


def main():
    admin = KafkaAdminClient(
        bootstrap_servers=[BOOTSTRAP_SERVERS],
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_oauth_token_provider=MSKTokenProvider(),
    )
    for topic in TOPICS:
        try:
            admin.create_topics([NewTopic(name=topic, num_partitions=4, replication_factor=3)])
            print(f"Topic '{topic}' créé.")
        except Exception as exc:
            print(f"'{topic}' : {exc}")
    admin.close()


if __name__ == "__main__":
    if BOOTSTRAP_SERVERS == "A_REMPLACER":
        print("Remplace BOOTSTRAP_SERVERS avant de lancer.")
        sys.exit(1)
    main()
