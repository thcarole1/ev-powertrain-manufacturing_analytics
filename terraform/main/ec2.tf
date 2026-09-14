# Bastion minimal, dans un sous-réseau du VPC par défaut (public, IP publique
# pour la sortie internet vers SSM — pas de passerelle NAT, voir ADR-005).
# À arrêter ou détruire en fin de session : facturé en continu sinon.
resource "aws_instance" "bastion" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = "t3.micro"
  subnet_id                   = data.aws_subnet.default_per_az[data.aws_availability_zones.available.names[0]].id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  iam_instance_profile        = aws_iam_instance_profile.bastion.name
  associate_public_ip_address = true

  # Aucune clé SSH (key_name volontairement omis) — accès uniquement via
  # AWS Systems Manager Session Manager.

  # Prépare tout dès le premier démarrage — évite de redécouvrir à chaque
  # nouvelle instance (git absent, dépendances manquantes, dépôt jamais
  # cloné) ce qu'on avait déjà découvert la fois précédente.
  # Permissions larges (777) sur /opt/project : simplification assumée pour
  # une instance de démonstration jetable, pas une pratique recommandée en
  # production — un vrai déploiement utiliserait un utilisateur/groupe dédié.
  user_data_replace_on_change = true
  user_data                   = <<-EOF
    #!/bin/bash
    set -euo pipefail
    dnf update -y
    dnf install -y git python3-pip

    mkdir -p /opt/project
    cd /opt/project
    git clone https://github.com/thcarole1/ev-powertrain-manufacturing_analytics.git .
    pip3 install -r aws/requirements.txt

    mkdir -p /opt/emr-jars
    cd /opt/emr-jars
    curl -sO https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.6/spark-sql-kafka-0-10_2.12-3.5.6.jar
    curl -sO https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.6/spark-token-provider-kafka-0-10_2.12-3.5.6.jar
    curl -sO https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar
    curl -sO https://repo1.maven.org/maven2/org/lz4/lz4-java/1.8.0/lz4-java-1.8.0.jar
    curl -sO https://repo1.maven.org/maven2/org/xerial/snappy/snappy-java/1.1.10.5/snappy-java-1.1.10.5.jar
    curl -sO https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.7/slf4j-api-2.0.7.jar
    curl -sO https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-runtime/3.3.4/hadoop-client-runtime-3.3.4.jar
    curl -sO https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-api/3.3.4/hadoop-client-api-3.3.4.jar
    curl -sO https://repo1.maven.org/maven2/commons-logging/commons-logging/1.1.3/commons-logging-1.1.3.jar
    curl -sO https://repo1.maven.org/maven2/com/google/code/findbugs/jsr305/3.0.0/jsr305-3.0.0.jar
    curl -sO https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar
    curl -sLO https://github.com/aws/aws-msk-iam-auth/releases/download/v2.3.8/aws-msk-iam-auth-2.3.8-all.jar

    aws s3 cp /opt/emr-jars/ s3://${aws_s3_bucket.emr_assets.bucket}/jars/ --recursive
    aws s3 cp /opt/project/aws/emr_detection_job.py s3://${aws_s3_bucket.emr_assets.bucket}/scripts/ 2>/dev/null || true

    chmod -R 777 /opt/project /opt/emr-jars
  EOF

  tags = { Name = "ev-powertrain-analytics-bastion" }
}
