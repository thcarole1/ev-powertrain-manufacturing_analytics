resource "aws_iam_role" "bastion" {
  name = "ev-powertrain-analytics-bastion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# Politique gérée AWS : autorise Session Manager, rien de plus large.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Accès Kafka scoppé au cluster précis, pas un accès MSK générique —
# principe du moindre privilège (cohérent avec ADR-001).
locals {
  msk_topic_arn_prefix = replace(aws_msk_serverless_cluster.this.arn, ":cluster/", ":topic/")
  msk_group_arn_prefix = replace(aws_msk_serverless_cluster.this.arn, ":cluster/", ":group/")
}

resource "aws_iam_role_policy" "msk_producer" {
  name = "ev-powertrain-analytics-msk-producer-access"
  role = aws_iam_role.bastion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Connect"
        Effect   = "Allow"
        Action   = "kafka-cluster:Connect"
        Resource = aws_msk_serverless_cluster.this.arn
      },
      {
        Sid    = "TopicWriteReadAndCreate"
        Effect = "Allow"
        Action = [
          "kafka-cluster:CreateTopic",
          "kafka-cluster:DescribeTopic",
          "kafka-cluster:WriteData",
          "kafka-cluster:ReadData",
        ]
        Resource = "${local.msk_topic_arn_prefix}/*"
      },
      {
        Sid    = "ConsumerGroupForVerification"
        Effect = "Allow"
        Action = [
          "kafka-cluster:AlterGroup",
          "kafka-cluster:DescribeGroup",
        ]
        Resource = "${local.msk_group_arn_prefix}/*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "bastion" {
  name = "ev-powertrain-analytics-bastion-profile"
  role = aws_iam_role.bastion.name
}
