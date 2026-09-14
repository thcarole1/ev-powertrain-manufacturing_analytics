# ADR-010 — Intégration continue via GitHub Actions

## Contexte

Dernière brique prévue par la roadmap : automatiser l'exécution des tests et la vérification du code d'infrastructure, sans dépendre d'une exécution manuelle avant chaque fusion.

## Décision

Un seul workflow GitHub Actions (`.github/workflows/tests.yml`), deux jobs :
- **`tests`** — installe Java (requis par PySpark) et Python, puis exécute les 30 tests du projet.
- **`terraform-validate`** — pour chacun des 3 modules (`bootstrap`, `main`, `data`), vérifie le formatage (`terraform fmt -check`) et la validité syntaxique (`terraform validate`), sans jamais initialiser de vrai backend ni exécuter de `plan`/`apply`.

Déclenché sur `pull_request` vers `main` (toutes les branches de travail) et sur `push` vers `main` uniquement (fusions et commits directs) — jamais les deux à la fois pour un même commit.

## Pourquoi

**`terraform init -backend=false` plutôt qu'un vrai backend** : valider la syntaxe ne nécessite pas d'accéder au state distant ni à un compte AWS — éviter cette dépendance signifie qu'aucun identifiant AWS n'a besoin d'être stocké dans les secrets GitHub, réduisant la surface d'exposition. Cohérent avec le principe de moindre privilège déjà appliqué ailleurs dans le projet (ADR-001, ADR-005).

**Jamais de `terraform apply` automatique** : le projet repose sur une discipline stricte de création/destruction manuelle de l'infrastructure entre les sessions (ADR-005 et suivants), pour maîtriser les coûts. Automatiser un `apply` en CI romprait cette discipline et pourrait déclencher des coûts sans supervision directe.

**Déclencheurs asymétriques (`push` limité à `main`, `pull_request` sur tout le reste)** : la configuration initiale déclenchait le workflow deux fois pour un même commit sur une branche avec une PR ouverte (une fois via `push`, une fois via `pull_request`) — repéré directement dans l'historique des exécutions GitHub Actions, pas anticipé à l'écriture. Corrigé en restreignant `push` à `main` seul.

## Incidents

**`terraform fmt -check` a révélé un fichier mal formaté** (`terraform/main/iam.tf`) — des blocs ajoutés manuellement via le terminal au fil de plusieurs sessions, jamais passés par `terraform fmt`. Corrigé par un simple `terraform fmt iam.tf`, sans changement de logique.

**Versions d'actions dépréciées** (`actions/checkout@v4`, `actions/setup-java@v4`, `hashicorp/setup-terraform@v3`) : GitHub a signalé leur exécution forcée sur une version de Node.js plus récente que celle qu'elles ciblaient — fonctionnel aujourd'hui, mais un signal à corriger avant qu'il ne devienne bloquant. Mis à jour vers les dernières versions majeures (`checkout@v6`, `setup-java@v5`, `setup-terraform@v4`).

## Preuve de fonctionnement

Workflow validé en conditions réelles sur GitHub : les deux jobs passent en environ 1m50s au total, sans avertissement après correctifs. Comportement des déclencheurs vérifié explicitement (une seule exécution par étape, confirmé dans l'historique des runs) plutôt que supposé correct après lecture du YAML.

## Conséquences

- La CI ne couvre que la syntaxe Terraform, jamais un vrai `plan` contre l'infrastructure réelle — une erreur de logique (mauvaise référence entre ressources, par exemple) ne serait détectée qu'au moment d'un `terraform plan` manuel, pas en amont par la CI.
- Le pipeline complet (MSK → EMR → S3 → Athena → Power BI) reste entièrement manuel, hors du périmètre de cette CI — cohérent avec la discipline de coûts du projet, mais signifie qu'aucune régression sur ce chemin ne serait détectée automatiquement.
