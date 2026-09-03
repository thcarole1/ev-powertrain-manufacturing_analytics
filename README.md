# EV Powertrain Manufacturing Analytics

## En bref

Pipeline de données temps réel simulant une ligne de production de moteurs électriques synchrones à aimants permanents (PMSM), de l'ingestion de capteurs IoT (température, vibration, courant, couple) jusqu'à la détection d'anomalies et la restitution métier.

Second projet de portfolio, complémentaire au projet [Electric Mobility Platform](LIEN_A_COMPLETER), axé sur des compétences non démontrées jusqu'ici : Kafka, Spark, et potentiellement Kubernetes/LLM en option.

## Architecture

```mermaid
flowchart LR
    A[Capteurs IoT simulés] --> B[Amazon MSK]
    B --> C[Traitement Spark / EMR]
    C --> D[S3 - Data Lake]
    D --> E[Glue Catalog]
    E --> F[Athena]
    F --> G[Power BI]
```

*Schéma à affiner au fil des phases — voir `docs/adr/` pour le détail des décisions.*

## Stack technique

| Domaine | Technologie |
|---|---|
| Ingestion streaming | Amazon MSK (Kafka managé) |
| Traitement | Spark (Glue puis EMR) |
| Stockage | S3 |
| Requêtage | Athena |
| Restitution | Power BI |
| Infrastructure | Terraform |
| CI/CD | GitHub Actions |

## État du projet

| Élément | Nombre |
|---|---|
| Phases terminées | 0 / à définir |
| ADR | 1 |
| Tests | 0 |

## Décisions d'architecture

Les décisions techniques significatives sont documentées dans [`docs/adr/`](docs/adr/), au format Contexte / Décision / Pourquoi / Conséquences.

- [ADR-001 — Utilisation du compte AWS existant, séparation par tags](docs/adr/0001-utilisation-compte-aws-existant.md)

## Démarrage

*Section à compléter une fois l'infrastructure initiale en place (prérequis, déploiement, tests).*
