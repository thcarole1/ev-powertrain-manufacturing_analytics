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
