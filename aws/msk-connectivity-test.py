"""Test de connectivité MSK Serverless — à exécuter sur le bastion EC2 uniquement.

Preuve de fonctionnement bout en bout : crée un topic, envoie un message,
le relit. Si le message envoyé apparaît dans la lecture, l'authentification
IAM, le réseau et le cluster fonctionnent tous ensemble.
"""

import sys
import time

from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import NewTopic
from kafka.sasl.oauth import AbstractTokenProvider
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

REGION = "eu-west-3"
TOPIC = "connectivity-test"
BOOTSTRAP_SERVERS = "A_REMPLACER"  # sortie Terraform : msk_bootstrap_brokers


class MSKTokenProvider(AbstractTokenProvider):
    def token(self):
        token, _ = MSKAuthTokenProvider.generate_auth_token(REGION)
        return token


def common_kwargs():
    return dict(
        bootstrap_servers=[BOOTSTRAP_SERVERS],
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_oauth_token_provider=MSKTokenProvider(),
    )


def main():
    print("1. Création du topic de test...")
    admin = KafkaAdminClient(**common_kwargs())
    try:
        # replication_factor=-1 : MSK Serverless gère la réplication lui-même,
        # on ne peut pas (et ne doit pas) la spécifier explicitement.
        admin.create_topics([NewTopic(name=TOPIC, num_partitions=1, replication_factor=-1)])
        print(f"   Topic '{TOPIC}' créé.")
    except Exception as exc:
        print(f"   (topic déjà existant ou erreur non bloquante : {exc})")
    admin.close()

    print("2. Envoi d'un message de test...")
    producer = KafkaProducer(**common_kwargs(), value_serializer=lambda v: v.encode("utf-8"))
    message = f"connectivity-test-{int(time.time())}"
    producer.send(TOPIC, value=message)
    producer.flush(timeout=30)
    producer.close()
    print(f"   Message envoyé : {message}")

    print("3. Lecture du message depuis le début du topic...")
    consumer = KafkaConsumer(
        TOPIC,
        **common_kwargs(),
        auto_offset_reset="earliest",
        consumer_timeout_ms=15000,
    )
    received = [msg.value.decode("utf-8") for msg in consumer]
    consumer.close()
    print(f"   Message(s) lu(s) : {received}")

    if message in received:
        print("\nSUCCÈS : le message envoyé a bien été relu depuis MSK Serverless.")
        sys.exit(0)
    else:
        print("\nÉCHEC : le message envoyé n'apparaît pas dans la lecture.")
        sys.exit(1)


if __name__ == "__main__":
    if BOOTSTRAP_SERVERS == "A_REMPLACER":
        print("Remplace BOOTSTRAP_SERVERS en haut du fichier par la sortie Terraform 'msk_bootstrap_brokers' avant de lancer.")
        sys.exit(1)
    main()
