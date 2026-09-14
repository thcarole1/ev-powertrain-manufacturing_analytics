# ADR-009 — Restitution via Power BI

## Contexte

Athena (ADR-008) rend les résultats de détection interrogeables en SQL. Reste la dernière brique de l'architecture cible : une restitution visuelle, exploitable sans écrire de requête.

## Décision

Power BI Desktop, connecté à Athena via le connecteur natif (pilote ODBC Amazon Athena), mode **Importer** (pas DirectQuery — volume de données faible, pas besoin de requêtes en temps réel à chaque interaction). Un tableau de bord unique : deux cartes KPI (unités testées, unités défectueuses), un graphique en anneau (répartition par statut), un tableau détaillé des unités défectueuses, un nuage de points (vibration vs équilibre de courant) avec les deux seuils de détection affichés comme lignes de référence.

## Pourquoi

**Connecteur natif Athena plutôt qu'ODBC générique** : Power BI propose un connecteur dédié qui simplifie la configuration par rapport à un pilote ODBC générique — cohérent avec l'objectif de rester sur des outils standards, explicables simplement.

**Mode Importer plutôt que DirectQuery** : le volume de données (quelques dizaines de lignes) rend le choix évident — Importer charge tout en mémoire une fois, sans latence de requête à chaque interaction avec le dashboard, pas de raison de solliciter Athena en continu pour un jeu de données aussi petit.

**Seuils affichés sur le nuage de points** : rend visuellement explicite *pourquoi* une unité est classée défectueuse, pas seulement *qu'elle l'est* — directement utile pour expliquer la logique de détection à un public non technique, dans l'esprit de la section "Comprendre ce projet en 2 minutes" déjà présente dans le README.

## Incident

**Le DSN ODBC perdait tous ses champs (sauf le nom) après un clic sur "Test".** Comportement du pilote Amazon Athena ODBC (x64) : le bouton de test valide la connexion avec les valeurs saisies à l'instant, mais ne les persiste pas dans le DSN Windows — un second "OK" sans repasser par "Test" a résolu le problème. Diagnostiqué en comparant les champs réellement enregistrés (vides) à ceux saisis puis testés avec succès, plutôt que de supposer une cause.

## Preuve de fonctionnement

Chaîne complète validée visuellement : MSK Serverless → EMR Serverless → S3 (Parquet) → Glue Catalog → Athena → Power BI. Les deux cartes affichent 35 et 8 — correspondance exacte avec les résultats obtenus directement depuis Athena et le job EMR (ADR-007, ADR-008). Capture d'écran du tableau de bord complet : `docs/images/powerbi-dashboard.png`.

## Conséquences

- Le tableau de bord n'est pas publié (pas de licence Power BI Service utilisée) — reste un fichier `.pbix` local, à partager par capture d'écran ou export PDF pour le portfolio.
- Les identifiants IAM utilisés pour la connexion sont ceux du projet Electric Mobility Platform, réutilisés tels quels après vérification qu'ils avaient les permissions nécessaires — pas d'utilisateur IAM dédié créé pour cette étape, à noter comme simplification si la question se pose en entretien.
- Les seuils affichés sur le nuage de points (1.5 pour la vibration, 0.85 pour l'équilibre de courant) sont saisis en dur dans le visuel, pas liés dynamiquement au code du job — à resynchroniser manuellement si les seuils de détection changent.
