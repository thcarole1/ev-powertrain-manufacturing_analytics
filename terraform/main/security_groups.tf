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

# MSK Serverless n'accepte du trafic que depuis le bastion, sur le port IAM (9098).
resource "aws_security_group" "msk" {
  name        = "ev-powertrain-analytics-msk-sg"
  description = "MSK Serverless - entree IAM (9098) depuis le bastion uniquement"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Kafka, authentification IAM, depuis le bastion"
    from_port       = 9098
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ev-powertrain-analytics-msk-sg" }
}
