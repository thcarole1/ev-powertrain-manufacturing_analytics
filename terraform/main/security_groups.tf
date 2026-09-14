# Le bastion n'a besoin d'AUCUNE règle entrante — SSM Session Manager
# n'initie jamais de connexion vers l'instance, seulement depuis elle.
resource "aws_security_group" "bastion" {
  name        = "ev-powertrain-analytics-bastion-sg"
  description = "Bastion EC2 pour le producteur Kafka - acces via SSM uniquement"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Sortie complete (SSM, MSK, depots de paquets)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ev-powertrain-analytics-bastion-sg" }
}

# Workers EMR Serverless — même principe que le bastion : sortie ouverte,
# aucune entrée directe (EMR gère lui-même l'accès à ses workers).
resource "aws_security_group" "emr_serverless" {
  name        = "ev-powertrain-analytics-emr-sg"
  description = "Workers EMR Serverless - job de detection"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Sortie vers MSK et services AWS"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ev-powertrain-analytics-emr-sg" }
}

# MSK Serverless accepte le trafic du bastion (producteur) ET des workers
# EMR Serverless (job de détection), sur le port IAM (9098) uniquement.
resource "aws_security_group" "msk" {
  name        = "ev-powertrain-analytics-msk-sg"
  description = "MSK Serverless - entree IAM (9098) depuis bastion et EMR"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Kafka, authentification IAM, depuis bastion et EMR Serverless"
    from_port       = 9098
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id, aws_security_group.emr_serverless.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ev-powertrain-analytics-msk-sg" }
}
