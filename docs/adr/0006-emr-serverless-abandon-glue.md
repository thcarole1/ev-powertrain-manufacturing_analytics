# ADR-006 — Détection via EMR Serverless (abandon de Glue)

## Contexte

Après MSK Serverless (ADR-005), l'étape suivante est le traitement Spark managé sur AWS. La roadmap prévoyait Glue en premier (Phase 3), EMR en second (Phase 6, migration documentée).

## Décision

**EMR Serverless dès aujourd'hui, Glue abandonné.** Pas de VPC dédié ni de connecteur Glue — un job Spark autonome (`aws/emr_detection_job.py`), connecté à MSK Serverless en IAM natif, sans dépendance à `anomaly/` (logique dupliquée volontairement, pour rester un fichier unique et lisible).

## Pourquoi

**Glue abandonné** : deux découvertes en cascade avant de dépenser le moindre crédit AWS.
1. Le connecteur Kafka *générique* de Glue ne supporte pas l'authentification IAM (doc officielle) — mais un connecteur *MSK dédié* existe et la supporte (article de blog AWS officiel), ce qui a corrigé une première fausse alerte.
2. Ce connecteur MSK dédié repose sur un modèle de connexion (`AuthenticationConfiguration`) que le fournisseur Terraform AWS ne supporte pas encore (ticket GitHub ouvert, ~173 jours). Créer la connexion à la main, hors Terraform, restait possible mais cassait l'infrastructure-as-code et complexifiait inutilement un projet de portfolio junior.

**EMR Serverless plutôt qu'EMR classique** : aucune gestion de cluster (dimensionnement, nœuds), coût nul à l'arrêt (facturé uniquement au calcul réellement consommé pendant un job) — pas de discipline de destruction entre sessions, contrairement à MSK.

## Incidents

Tous liés à des permissions IAM ou des JARs manquants — aucun ne remettait en cause l'architecture, mais leur accumulation a rendu la session longue et confuse. Résolus un par un, dans l'ordre où ils sont apparus :

1. **Sous-réseaux privés, aucun accès internet** — les workers EMR Serverless ne peuvent pas télécharger les dépendances Kafka/IAM via `--packages` (pas de passerelle NAT, décision assumée dans ADR-005). Contourné en téléchargeant les 12 JARs nécessaires (connecteur Kafka Spark 3.5.6 et ses dépendances transitives, `aws-msk-iam-auth`) depuis le bastion, puis en les référençant depuis S3 via `spark.jars`.
2. **`s3:PutObject` manquant** sur le rôle du bastion — sa policy ne couvrait que MSK, pas le nouveau bucket S3.
3. **`emr-serverless:StartJobRun` manquant** sur le rôle du bastion.
4. **`iam:PassRole` manquant** — le bastion doit explicitement être autorisé à transmettre le rôle d'exécution du job à EMR Serverless.
5. **`emr-serverless:GetJobRun` trop restreint** — la policy ne portait que sur l'application, pas sur les jobs individuels qu'elle contient (`/jobruns/*` manquant).
6. **Journaux non configurés** — un premier job a réussi (`SUCCESS`) sans qu'aucune sortie ne soit récupérable, faute de destination de logs S3 explicite (`--configuration-overrides`).
7. **Commande CLI trop longue** — `start-job-run` avec les 12 JARs en ligne dépassait la capacité de collage fiable du terminal SSM, tronquant silencieusement la commande. Résolu en passant par des fichiers JSON (`job.json`, `logs.json`) plutôt qu'une ligne de commande unique.
8. **`terraform destroy` bloqué** — l'application EMR Serverless reste `STARTED` après un job, un état que Terraform ne peut pas détruire directement. Nécessite un arrêt explicite (`aws emr-serverless stop-application`) avant destruction.

## Preuve de fonctionnement

Deux exécutions réelles, données lues depuis MSK Serverless (IAM), job exécuté sur EMR Serverless :
- 5 unités : 2/2 défectueuses détectées, 0 faux positif (`docs/proofs/emr-serverless-detection-proof.txt`)
- 55 unités (cumul de deux envois) : 12/12 défectueuses détectées, 0 faux positif (`docs/proofs/emr-serverless-detection-proof-55units.txt`)

Infrastructure détruite en fin de session.

## Conséquences

- Le job Spark duplique la logique de `anomaly/features.py` et `anomaly/classify.py` plutôt que d'importer le package — accepté comme simplification délibérée (éviter un mécanisme de packaging `--py-files` non testé), à corriger si le projet évolue vers plusieurs jobs Glue/EMR partageant cette logique.
- Le processus de démarrage du bastion (`user_data`) automatise maintenant le clonage du dépôt, l'installation des dépendances et le téléchargement des JARs — mais clone la branche `main`, pas la branche de travail en cours. Un script ou une nouvelle fonctionnalité ajoutée sur une branche non fusionnée n'est pas visible au démarrage tant qu'elle n'est pas mergée.
