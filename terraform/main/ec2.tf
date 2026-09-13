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

  tags = { Name = "ev-powertrain-analytics-bastion" }
}
