# ADR-003 — Détection en streaming (session window, watermark, résilience)

## Contexte

La version batch (ADR-002) prouve que la logique de détection fonctionne, mais relit l'intégralité de Kafka à chaque exécution — incompatible avec un flux qui ne s'arrête jamais. Cet ADR documente le passage à `spark.readStream`, ainsi que les incidents rencontrés et corrigés en cours de route.

## Décision

- **Colonne de temps dédiée** : `event_time`, l'horloge murale réelle au moment de l'envoi — le champ `t` existant (temps relatif au test d'une unité) ne peut pas servir de colonne de watermark, puisqu'il repart à zéro à chaque nouvelle unité.
- **`session_window`, pas une fenêtre fixe** : chaque unité ferme sa session automatiquement dès qu'aucune nouvelle mesure n'arrive pendant `SESSION_GAP` (8 secondes) — pas besoin de connaître à l'avance la durée exacte d'un test.
- **Watermark de 15 secondes**, pour absorber un retard de traitement Kafka/Spark sans perdre de données légitimement en retard.
- **Une configuration de fréquences d'échantillonnage allégée** (`StreamingDemoConfig`), distincte de celle du batch, réservée à la démonstration temps réel.
- **Un message de purge automatique** en fin d'envoi, pour forcer le watermark à avancer au-delà de la dernière vraie donnée.
- **Périmètre limité au capteur vibration pour cette itération** — la détection du déséquilibre de phase (courant) et la classification complète (jointure des trois capteurs) sont reportées à une prochaine étape.
- **`current_features` réécrit sans `.pivot()`** — remplacé par une agrégation conditionnelle, pour garantir un comportement identique en batch et en streaming.

## Pourquoi

**Session window plutôt que fenêtre fixe** : une fenêtre tumbling de 30 secondes aurait supposé une durée de test connue et fixe à l'avance ; `session_window` s'adapte à la fin réelle du flux de données pour une unité donnée, plus fidèle à un vrai test dont la durée peut varier.

**Configuration allégée pour la démo streaming** : la première tentative, à pleine fidélité (jusqu'à 1000 Hz sur le courant, ~93 000 messages/unité), a provoqué une fragmentation de session sur plusieurs unités — un test entier de 30 secondes découpé en 2 à 6 sessions distinctes pour la même unité. Diagnostic : avec plusieurs unités simulées en parallèle (threading Python, donc soumis au GIL), le volume de messages à envoyer par seconde simulée (jusqu'à ~18 000 msg/s cumulés avec 6 unités actives) dépassait ce que le GIL pouvait exécuter en temps réel, créant des trous de silence supérieurs au gap de session (8s) et déclenchant des fermetures prématurées. Réduire les fréquences d'un facteur ~15 (vibration 100→50 Hz, courant 1000→50 Hz) a résolu le problème sans toucher à la logique de génération des signaux ni à la fidélité du batch.

**Message de purge** : le watermark Spark n'avance que sur réception de nouvelles données, jamais tout seul avec le temps réel qui passe. Une fois la dernière unité terminée, plus aucune donnée n'arrivant jamais, les sessions encore ouvertes (la ou les dernières unités) restaient bloquées indéfiniment — observé concrètement lors d'un test où 4 unités sur 10 ne se sont jamais finalisées sans intervention. Un message de purge, avec un `event_time` délibérément dans le futur, force le watermark à franchir le seuil nécessaire pour débloquer tout ce qui est en attente.

**Vibration seule pour cette itération** : combiner les trois capteurs (vibration, température, courant) nécessiterait une jointure stream-stream entre plusieurs agrégations déjà finalisées, avec ses propres contraintes de watermark et de fenêtre temporelle — un problème distinct de ce qui vient d'être résolu, traité séparément plutôt qu'assemblé à la hâte.

## Conséquences

- La détection en streaming ne couvre actuellement que le scénario de défaut de roulement (vibration) ; le déséquilibre de phase reste détecté uniquement en batch pour l'instant.
- Deux configurations de fréquences coexistent (`SimulationConfig` pour le batch, `StreamingDemoConfig` pour le streaming) — à garder synchronisées si les seuils de détection évoluent.
- Le mécanisme de purge est un contournement pragmatique pour une démo qui s'arrête ; un pipeline réellement continu (unités arrivant indéfiniment) n'en aurait pas besoin, le watermark avançant naturellement avec le flux permanent de nouvelles données.
- Deux tests couvrent le comportement de `session_window` (regroupement des événements rapprochés, séparation des événements éloignés, indépendance entre unités) sans dépendre d'un vrai cluster Kafka.
