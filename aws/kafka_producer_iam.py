"""Variante IAM du producteur Kafka, pour MSK Serverless uniquement.

kafka-python doit être <= 2.0.9 pour que l'approche OAUTHBEARER de
aws-msk-iam-sasl-signer-python fonctionne (incident rencontré ce jour :
kafka-python 2.1.0+ a introduit un changement cassant — voir requirements.txt
de ce dossier, distinct de celui du projet principal qui n'a pas cette
contrainte, Kafka local n'utilisant pas l'authentification IAM).
"""

import json

from kafka import KafkaProducer
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

REGION = "eu-west-3"


class MSKTokenProvider:
    """Pas d'héritage volontaire — voir aws/msk-connectivity-test.py pour le détail."""

    def token(self):
        token, _ = MSKAuthTokenProvider.generate_auth_token(REGION)
        return token


def build_iam_producer(bootstrap_servers):
    return KafkaProducer(
        bootstrap_servers=[bootstrap_servers],
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_oauth_token_provider=MSKTokenProvider(),
        key_serializer=lambda k: k.encode("utf-8"),
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )
