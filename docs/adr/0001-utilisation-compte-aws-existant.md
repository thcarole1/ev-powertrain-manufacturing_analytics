# ADR-001 — Utilisation du compte AWS existant, séparation par tags

## Contexte

Le projet EV Powertrain Manufacturing Analytics est un second projet de portfolio, complémentaire au projet Electric Mobility Platform déjà déployé sur AWS. Un seul compte AWS est disponible pour les deux projets.

## Décision

Le projet est déployé sur le compte AWS existant, sans création de compte dédié ni mise en place d'AWS Organizations. La séparation entre les deux projets est assurée par une stratégie de tags systématique et un budget dédié.

## Pourquoi

La création d'un compte dédié (AWS Organizations, SSO, comptes séparés) apporterait une isolation plus stricte, mais représente un effort de mise en place non aligné avec les compétences prioritaires du projet (Kafka, Spark). Le risque de collision de ressources entre les deux projets est jugé maîtrisable par une convention de nommage et de tags stricte appliquée dès le premier déploiement.

## Conséquences

- Toute ressource créée pour ce projet porte le tag `Project=ev-powertrain-analytics`, sans exception, y compris via les `default_tags` du provider Terraform.
- Le suivi des coûts par Cost Explorer se fait par filtre de tag et non par compte, ce qui est moins immédiat qu'une facturation nativement séparée.
- Une alerte AWS Budgets dédiée est créée en filtrant sur ce tag, dès la Phase 0.
- Compromis de sécurité assumé : les rôles IAM du projet cohabitent dans le même compte que le premier projet. Le principe du moindre privilège reste appliqué au niveau des rôles applicatifs, mais aucune isolation compte-à-compte n'existe entre les deux projets.
