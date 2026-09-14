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

# Oublié initialement : le bastion doit pouvoir écrire sur le bucket EMR
# (JARs, script du job) — sa policy ne couvrait jusqu'ici que MSK.
resource "aws_iam_role_policy" "bastion_s3" {
  name = "ev-powertrain-analytics-bastion-s3-access"
  role = aws_iam_role.bastion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "UploadJarsAndScript"
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.emr_assets.arn,
        "${aws_s3_bucket.emr_assets.arn}/*",
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "bastion" {
  name = "ev-powertrain-analytics-bastion-profile"
  role = aws_iam_role.bastion.name
}

resource "aws_iam_role_policy" "bastion_emr" {
  name = "ev-powertrain-analytics-bastion-emr-access"
  role = aws_iam_role.bastion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "StartAndCheckEmrJob"
      Effect = "Allow"
      Action = ["emr-serverless:StartJobRun", "emr-serverless:GetJobRun"]
      Resource = [
        aws_emrserverless_application.detection.arn,
        "${aws_emrserverless_application.detection.arn}/jobruns/*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "bastion_pass_role" {
  name = "ev-powertrain-analytics-bastion-passrole"
  role = aws_iam_role.bastion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "PassEmrJobRole"
      Effect   = "Allow"
      Action   = "iam:PassRole"
      Resource = aws_iam_role.emr_serverless_job.arn
    }]
  })
}

# Bucket data lake désormais dans un module Terraform séparé (terraform/data,
# persistant) — accès via terraform_remote_state, plus de ressource locale.
resource "aws_iam_role_policy" "bastion_data_lake" {
  name = "ev-powertrain-analytics-bastion-datalake-access"
  role = aws_iam_role.bastion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadResults"
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        data.terraform_remote_state.data_lake.outputs.data_lake_bucket_arn,
        "${data.terraform_remote_state.data_lake.outputs.data_lake_bucket_arn}/*",
      ]
    }]
  })
}
