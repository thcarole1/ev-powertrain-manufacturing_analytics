# ADR-008 — Requêtage Athena sur le data lake persistant

## Contexte

Le module `terraform/data` (ADR-007) persiste les résultats de détection en Parquet sur S3. Reste à les rendre interrogeables en SQL — le rôle d'Athena dans l'architecture cible.

## Décision

- **Table Glue Data Catalog définie explicitement**, schéma écrit à la main (7 colonnes, déjà connues du job EMR), plutôt qu'un Glue Crawler.
- **Groupe de travail Athena dédié**, avec ses résultats de requêtes stockés dans un sous-dossier du bucket persistant existant (`athena-query-results/`), pas un nouveau bucket.
- **Les deux ressources vivent dans `terraform/data`**, pas `terraform/main` — cohérent avec ADR-007, elles décrivent des données qui doivent survivre à la destruction de l'infrastructure éphémère entre les sessions.

## Pourquoi

**Schéma explicite plutôt qu'un Crawler** : un Crawler sert à découvrir un schéma inconnu ou évolutif — ici, le schéma de sortie du job EMR est fixe et déjà écrit dans le code (`emr_detection_job.py`). Un Crawler aurait ajouté une dépendance et un coût (facturé au DPU-heure, minimum 10 minutes par exécution) pour reformuler une information qu'on possède déjà.

**Dossier partagé plutôt qu'un second bucket** : les résultats de requêtes Athena n'ont pas de raison d'être séparés physiquement des données qu'ils interrogent — un sous-dossier du bucket existant suffit, sans complexifier l'inventaire de ressources.

## Preuve de fonctionnement

Deux requêtes réelles depuis la console Athena, sur les 35 unités déjà persistées (ADR-007) :
- `SELECT * FROM detection_results LIMIT 10` — colonnes correctement typées, données lisibles.
- Agrégation (`COUNT`, `SUM` conditionnel) — **35 unités, 8 défectueuses**, correspondance exacte avec le résultat obtenu directement depuis le job EMR Serverless.

Détail dans `docs/proofs/athena-query-proof.txt`.

## Conséquences

- **Coût négligeable, vérifié** : Glue Data Catalog gratuit jusqu'à 1 million d'objets/requêtes mensuels (2 objets utilisés ici) ; Athena facturé $5/To scanné avec un minimum de 10 Mo par requête — de l'ordre du millième de centime pour l'usage actuel. Pas de discipline de destruction nécessaire, cohérent avec le reste du module persistant.
- Le schéma de la table Glue doit rester manuellement synchronisé avec celui du job EMR (`emr_detection_job.py`) — un changement de colonne côté job sans mise à jour de `terraform/data/glue_catalog.tf` romprait le requêtage sans erreur explicite (colonnes manquantes ou mal typées, pas un échec bloquant).
- Prochaine étape naturelle : connecter Power BI à Athena pour la restitution visuelle.
