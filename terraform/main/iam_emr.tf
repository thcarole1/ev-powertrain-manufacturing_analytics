resource "aws_iam_role" "emr_serverless_job" {
  name = "ev-powertrain-analytics-emr-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "emr-serverless.amazonaws.com" }
    }]
  })
}

# Même logique de moindre privilège que le rôle du bastion (ADR-005) —
# accès au cluster MSK précis, pas un accès MSK générique.
resource "aws_iam_role_policy" "emr_serverless_msk" {
  name = "ev-powertrain-analytics-emr-msk-access"
  role = aws_iam_role.emr_serverless_job.id

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
        Sid    = "TopicRead"
        Effect = "Allow"
        Action = [
          "kafka-cluster:DescribeTopic",
          "kafka-cluster:ReadData",
        ]
        Resource = "${local.msk_topic_arn_prefix}/*"
      },
      {
        Sid    = "ConsumerGroup"
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

resource "aws_iam_role_policy" "emr_serverless_s3" {
  name = "ev-powertrain-analytics-emr-s3-access"
  role = aws_iam_role.emr_serverless_job.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ScriptAndLogs"
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.emr_assets.arn,
        "${aws_s3_bucket.emr_assets.arn}/*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "emr_serverless_data_lake" {
  name = "ev-powertrain-analytics-emr-datalake-access"
  role = aws_iam_role.emr_serverless_job.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "WriteResults"
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.data_lake.arn,
        "${aws_s3_bucket.data_lake.arn}/*",
      ]
    }]
  })
}
