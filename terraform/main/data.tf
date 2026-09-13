# Réutilisation du VPC par défaut (ADR-005) — pas de VPC dédié pour ce projet.

data "aws_vpc" "default" {
  default = true
}

data "aws_availability_zones" "available" {
  state = "available"
}

# Un seul sous-réseau par AZ (le sous-réseau par défaut de chaque zone,
# garanti unique) — MSK Serverless refuse plusieurs sous-réseaux dans la
# même AZ, ce que data.aws_subnets (tous les sous-réseaux du VPC) ne
# garantissait pas.
data "aws_subnet" "default_per_az" {
  for_each          = toset(data.aws_availability_zones.available.names)
  vpc_id            = data.aws_vpc.default.id
  availability_zone = each.value
  default_for_az    = true
}

# AMI Amazon Linux 2023 la plus récente — toujours à jour, pattern standard AWS.
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}
