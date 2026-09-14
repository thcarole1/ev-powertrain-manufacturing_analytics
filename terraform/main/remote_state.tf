# Lit les sorties du module terraform/data (bucket persistant), sans jamais
# pouvoir le modifier ni le détruire depuis ce module — juste une lecture
# de son state distant.
data "terraform_remote_state" "data_lake" {
  backend = "s3"
  config = {
    bucket = "ev-powertrain-analytics-tfstate-fb5f6db7"
    key    = "data/terraform.tfstate"
    region = "eu-west-3"
  }
}
