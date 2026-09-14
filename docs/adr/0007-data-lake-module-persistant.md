# ADR-007 — Module Terraform séparé pour le data lake persistant

## Contexte

Le job EMR Serverless (ADR-006) écrit désormais ses résultats de détection sur S3, au format Parquet — préalable nécessaire à Athena. Ce bucket vivait jusqu'ici dans `terraform/main`, détruit systématiquement en fin de session pour maîtriser les coûts (MSK, bastion, EMR). Un bucket S3 contenant seulement quelques Parquet ne coûte presque rien au repos, contrairement à MSK/EMR — le détruire à chaque fois revenait à perdre des données réutilisables sans raison de coût réelle.

## Décision

Nouveau module Terraform, `terraform/data/`, avec son propre backend (state distinct dans le même bucket S3 de state, clé `data/terraform.tfstate`). Il contient uniquement le bucket S3 du data lake. `terraform/main` y accède en lecture seule via `terraform_remote_state`, sans jamais pouvoir le modifier ni le détruire depuis ce module.

`terraform/main` reste détruit à chaque fin de session comme avant ; `terraform/data` ne s'applique qu'une fois et reste en place jusqu'à la fin du projet.

## Pourquoi

**Module séparé plutôt qu'un simple `prevent_destroy`** : un `lifecycle { prevent_destroy = true }` aurait suffi à empêcher la suppression accidentelle, mais aurait aussi bloqué `terraform destroy` sur tout `terraform/main` (Terraform refuse de détruire un module contenant une ressource protégée, même si les autres ressources du même module sont censées disparaître). Un module distinct, avec son propre cycle de vie, évite ce blocage : on peut détruire l'un sans toucher à l'autre.

**Backend séparé plutôt qu'un state partagé** : un seul state pour tout aurait mélangé des ressources à durées de vie complètement différentes (une session vs tout le projet), rendant `terraform plan`/`destroy` ambigus sur ce qui doit réellement disparaître.

## Incident

**`AccessDenied` sur `s3:DeleteObject`, au second job écrit sur le même chemin.** Le script du job (`mode("overwrite")`) supprime les anciens fichiers avant d'écrire les nouveaux — la policy IAM du job ne couvrait que `PutObject`/`GetObject`/`ListBucket`, jamais `DeleteObject`. Le tout premier job (5 unités, rien à supprimer) avait réussi, masquant le problème jusqu'à un second job sur le même chemin. Corrigé par l'ajout explicite de `s3:DeleteObject` à la policy.

## Preuve de fonctionnement

Cycle complet validé : `terraform/main` appliqué → job EMR écrit sur le bucket persistant (35 unités, 8/8 défectueuses détectées, 0 faux positif — `docs/proofs/emr-persistent-bucket-proof.txt`) → `terraform/main` détruit → **le bucket et son contenu survivent**, vérifié après destruction (`aws s3 ls` confirme la présence des fichiers Parquet).

## Conséquences

- Deux commandes `terraform apply`/`destroy` à exécuter séparément selon l'intention (`terraform/data` une fois pour toutes, `terraform/main` à chaque session) — légèrement plus de discipline opérationnelle qu'un module unique, compensée par l'absence de risque de perte accidentelle.
- Le bucket persistant accumule des coûts de stockage S3 négligeables mais réels sur toute la durée du projet — à surveiller si le volume de données croît significativement (pas un risque à ce stade).
- Toute nouvelle ressource devant survivre entre les sessions (par exemple, une future base Glue Catalog pour Athena) suivra ce même pattern : `terraform/data`, jamais `terraform/main`.
