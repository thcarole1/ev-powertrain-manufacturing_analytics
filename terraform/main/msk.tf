resource "aws_msk_serverless_cluster" "this" {
  cluster_name = "ev-powertrain-analytics-msk"

  vpc_config {
    subnet_ids         = [for s in data.aws_subnet.default_per_az : s.id]
    security_group_ids = [aws_security_group.msk.id]
  }

  client_authentication {
    sasl {
      iam {
        enabled = true
      }
    }
  }

  tags = { Name = "ev-powertrain-analytics-msk" }
}
