# ADR-005 — Architecture de déploiement AWS (backend, VPC, MSK Serverless, bastion)

## Contexte

Le pipeline (simulateur, Kafka, détection Spark) est validé en local. Cet ADR documente le passage à un déploiement AWS réel : Kafka via Amazon MSK, préalable aux phases suivantes (Glue/EMR, S3, Athena, Power BI).

## Décision

- **Backend Terraform** : état distant sur S3 (bucket `ev-powertrain-analytics-tfstate-fb5f6db7`), verrouillage via DynamoDB (`ev-powertrain-analytics-tfstate-lock`), tous deux créés par un module de bootstrap séparé, en state local (problème de l'œuf et de la poule).
- **VPC** : réutilisation du VPC par défaut du compte, via sources de données Terraform (`data "aws_vpc"`, `data "aws_subnets"`) — pas de VPC dédié créé pour ce projet.
- **MSK Serverless** (pas Provisioned) — décision esquissée plus tôt dans le projet, actée ici.
- **Accès au cluster** : MSK Serverless n'expose aucun accès public, uniquement accessible depuis l'intérieur du VPC. Une instance EC2 minimale, dans un sous-réseau public du VPC par défaut, sert de bastion pour exécuter le producteur Kafka (`stream_to_kafka_realtime.py`). Accès géré exclusivement via AWS Systems Manager Session Manager — aucune clé SSH, aucune règle entrante sur le groupe de sécurité du bastion.
- **Pas de passerelle NAT** : le bastion utilise directement un sous-réseau public (IP publique, sortie via la passerelle internet déjà présente sur le VPC par défaut) — SSM n'a besoin que d'un accès sortant. MSK Serverless reste dans des sous-réseaux sans sortie internet, n'en ayant pas besoin.
- **Glue** (traitement Spark, phase suivante) lira MSK directement, nativement dans le VPC, sans passer par le bastion.

## Pourquoi

**VPC par défaut plutôt qu'un VPC dédié** : la création et la gestion d'un VPC (sous-réseaux, tables de routage, passerelle internet) a déjà été démontrée sur un projet antérieur (Electric Mobility Platform, via MWAA) — la refaire ici n'apporterait rien de nouveau à démontrer, pour un coût de temps de développement réel. L'effort est concentré sur MSK et Glue, les compétences différenciantes de ce projet.

**Pas de passerelle NAT** : une passerelle NAT coûte environ 32 $/mois si laissée active en continu, pour un besoin d'accès sortant ponctuel et minime (le bastion, uniquement pendant les sessions de travail). Un sous-réseau public avec IP publique évite ce coût, sans compromis de sécurité significatif dans la mesure où aucune règle entrante n'est ouverte — seul le trafic initié depuis l'instance elle-même (vers SSM) est concerné.

**SSM plutôt que SSH** : élimine la gestion de paires de clés et toute exposition du port 22, cohérent avec le principe du moindre privilège déjà appliqué sur ce projet (ADR-001).

## Conséquences

- Le VPC par défaut est partagé avec toute autre charge présente sur ce compte AWS — cohérent avec le choix déjà fait de ne pas isoler ce projet par un compte dédié (ADR-001), mais signifie que les groupes de sécurité doivent être explicitement scopés à ce projet pour éviter toute interférence.
- Le bastion EC2 est une ressource facturée en continu si elle n'est pas arrêtée ou détruite entre les sessions — à intégrer à la checklist de fin de session, au même titre que MSK.
- Toute future migration vers un VPC dédié (si l'isolation devenait nécessaire) impliquerait de revoir cet ADR et de recréer les ressources réseau-dépendantes.

## Incidents

### Sous-réseaux dans la même zone de disponibilité

`data.aws_subnets` retournait tous les sous-réseaux du VPC par défaut, dont certains partagent la même AZ — MSK Serverless refuse explicitement ce cas (`BadRequestException`). Corrigé en sélectionnant précisément un sous-réseau par AZ via `data.aws_subnet` avec `default_for_az = true`, itéré sur `data.aws_availability_zones`.

### Jeu de caractères restreint sur les descriptions de groupe de sécurité

Les descriptions rédigées en français correct (accents, tiret cadratin) ont été rejetées par la validation AWS (`^[0-9A-Za-z_ .:/()#,@\[\]+=&;{}!$*-]*$`) — spécifique aux champs `description` d'`aws_security_group`, pas aux autres ressources. Corrigé en réécrivant ces descriptions sans caractères accentués.

### Incompatibilité de version `kafka-python` avec l'authentification IAM

`kafka-python` installé par défaut (`3.0.11`, via `pip install kafka-python`) a une architecture interne différente de celle attendue par `aws-msk-iam-sasl-signer-python`, provoquant un `ModuleNotFoundError` puis un `KafkaTimeoutError` au moment de la négociation SASL. Diagnostic confirmé par une recherche externe : `kafka-python` a introduit un changement cassant en version 2.1.0 sur la gestion SASL, documenté par la bibliothèque de signature IAM elle-même comme cassant leur approche OAUTHBEARER. Corrigé en épinglant `kafka-python==2.0.2` dans `aws/requirements.txt`, distinct du `requirements.txt` principal (Kafka local, sans authentification IAM, non concerné par cette contrainte).

### Permission IAM manquante pour la lecture (`ReadData`)

La policy IAM du bastion accordait `CreateTopic`, `DescribeTopic`, `WriteData`, mais pas `ReadData` — un oubli de conception, pas une erreur AWS. La création de topic et l'envoi de messages fonctionnaient, la lecture échouait avec `TopicAuthorizationFailedError`. Corrigé par l'ajout explicite de `kafka-cluster:ReadData` sur la ressource topic.

### `replication_factor=-1` refusé par le client, alors que MSK Serverless l'impose

MSK Serverless gère lui-même la réplication et n'accepte pas de valeur explicite côté client — mais `kafka-python==2.0.2` refuse `-1` (convention "laisser le serveur décider" dans d'autres écosystèmes Kafka) avec une erreur de validation locale, avant même d'atteindre le serveur. Contourné en envoyant `replication_factor=3` : une valeur positive quelconque satisfait la validation du client, sans effet réel côté serveur.

## Preuve de fonctionnement

Bout en bout, sur le cluster réel : création de 4 topics, diffusion de 5 unités simulées complètes (le vrai simulateur du projet, pas un message de test), relecture confirmant un total de 15 000 messages sur `sensor-vibration` (5 unités × 100 Hz × 30s — correspondance exacte), structure JSON correcte, signature de défaut de roulement visible sur l'unité marquée défectueuse dans le manifeste.

**Test de connectivité** (produire, relire, confirmer) :
![Test de connectivité MSK Serverless](images/msk-connectivity-test-proof.png)

**Pipeline réel du projet, 5 unités, vérification du volume** :
![Diffusion des 5 unités et vérification des 15 000 messages](images/msk-real-pipeline-proof.png)

Infrastructure détruite en fin de session (`terraform destroy`) pour éviter les coûts continus — à redéployer via `terraform apply` le moment venu, sans perte : le state distant (S3) et le code restent intacts.
