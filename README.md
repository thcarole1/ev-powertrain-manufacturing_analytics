# EV Powertrain Manufacturing Analytics

## En bref

Pipeline de données temps réel simulant une ligne de production de moteurs électriques synchrones à aimants permanents (PMSM), de l'ingestion de capteurs IoT (température, vibration, courant, couple) jusqu'à la détection d'anomalies et la restitution métier.

Second projet de portfolio, complémentaire au projet [Electric Mobility Platform](LIEN_A_COMPLETER), axé sur des compétences non démontrées jusqu'ici : Kafka, Spark, et potentiellement Kubernetes/LLM en option.

**État actuel : pipeline batch et streaming (1 capteur et 3 capteurs) tous validés en local (Kafka + Spark, sans AWS pour l'instant).** Le déploiement sur AWS MSK/Glue est la prochaine étape, pas encore réalisée.

## Résultats clés

**Batch** — précision et rappel de 1.00 sur 50 unités testées.

![Résultats de détection](docs/images/detection_results.png)

**Streaming, 3 capteurs, validé à grande échelle** — détection combinée (roulement via vibration, déséquilibre de phase via courant) sur 50 unités simulées en parallèle à rythme réaliste : **14/14 unités défectueuses détectées, 0 faux positif** sur les 36 unités saines. Architecture découplée (trois flux streaming indépendants + jointure batch séparée) après l'abandon d'une jointure stream-stream native, qui se bloquait de façon non résolue — détail complet et incidents dans [ADR-004](docs/adr/0004-architecture-decouplee-streaming-3-capteurs.md).

## Pipeline streaming (3 capteurs, architecture découplée)

```mermaid
flowchart TD
    A["Kafka — 3 topics"] --> B["3 requêtes streaming<br/>indépendantes (session window)"]
    B --> C["3 fichiers JSON Lines<br/>résultats finalisés"]
    C --> D["Job batch : déduplication<br/>puis jointure sur unit_id"]
    D --> E["Classification combinée"]
```

## Architecture cible (AWS, à déployer)

```mermaid
flowchart LR
    A["Simulateur Python"] --> B["Amazon MSK"]
    B --> C["Traitement Spark<br/>EMR ou Glue"]
    C --> D["S3 - Data Lake"]
    D --> E["Glue Catalog"]
    E --> F["Athena"]
    F --> G["Power BI"]
```

## Stack technique

| Domaine | Technologie | Statut |
|---|---|---|
| Simulation de données | Python (numpy) | Fait |
| Ingestion streaming | Kafka (local, KRaft) → Amazon MSK | Local fait, AWS à faire |
| Traitement batch | PySpark (`spark.read`) | Fait |
| Traitement streaming (1 capteur) | PySpark (`spark.readStream`, session window) | Fait |
| Traitement streaming (3 capteurs) | Architecture découplée (3 flux + jointure batch) | Fait, validé à 50 unités |
| Détection d'anomalie | Seuils calibrés, PySpark | Fait |
| Stockage | — | À faire |
| Requêtage | — | À faire |
| Restitution | — | À faire |
| Infrastructure | — | À faire |
| CI/CD | — | À faire |

## État du projet

| Élément | Nombre |
|---|---|
| Phases terminées | Cadrage Phase 0 + validation locale Kafka/Spark (batch, streaming 1 et 3 capteurs) |
| ADR | 4 |
| Tests | 30 |

## Utilisation locale

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sous Windows hors WSL
pip install -r requirements.txt
python -m pytest tests/ -v

# Cluster Kafka local (voir local-dev/kafka/docker-compose.yml)
docker compose -f local-dev/kafka/docker-compose.yml up -d
```

**Batch :**
```bash
python stream_to_kafka.py --num-units 50
python detect_anomalies_batch.py
```

**Streaming, 1 capteur** (deux terminaux) :
```bash
python detect_anomalies_streaming.py
```
```bash
python stream_to_kafka_realtime.py --num-units 10
```

**Streaming, 3 capteurs** (deux terminaux, puis jointure séparée) :
```bash
python stream_sensors_to_files.py
```
```bash
python stream_to_kafka_realtime.py --num-units 50
```
Une fois les unités finalisées (`Ctrl+C` sur le premier terminal) :
```bash
python detect_anomalies_from_streaming_files.py
```

Détail complet des approches et incidents rencontrés : [ADR-002](docs/adr/0002-simulation-capteurs-iot-test-electrique-final.md) (simulateur, aliasing), [ADR-003](docs/adr/0003-detection-streaming-session-window-watermark.md) (streaming 1 capteur), [ADR-004](docs/adr/0004-architecture-decouplee-streaming-3-capteurs.md) (streaming 3 capteurs, architecture découplée).

## Décisions d'architecture

- [ADR-001 — Utilisation du compte AWS existant, séparation par tags](docs/adr/0001-utilisation-compte-aws-existant.md)
- [ADR-002 — Simulation des capteurs IoT pour le test électrique final](docs/adr/0002-simulation-capteurs-iot-test-electrique-final.md)
- [ADR-003 — Détection en streaming (session window, watermark, résilience)](docs/adr/0003-detection-streaming-session-window-watermark.md)
- [ADR-004 — Architecture découplée pour la détection streaming à 3 capteurs](docs/adr/0004-architecture-decouplee-streaming-3-capteurs.md)

## Prochaines étapes

- Décision à trancher : déploiement AWS (MSK Serverless envisagé) vs poursuite en local
