# ADR-002 — Simulation des capteurs IoT pour le test électrique final

## Contexte

Le simulateur doit générer des données représentatives d'un test électrique de fin de ligne sur des moteurs PMSM, avec une proportion d'unités présentant un défaut d'assemblage, pour alimenter la détection d'anomalie en aval (Spark, Phase 3).

## Décision

- Un seul stade de test simulé : le test électrique final (moteur en rotation/sous tension), seul stade où les quatre types de capteurs retenus (température, vibration, courant, couple) ont un sens physique.
- Durée de test : 30 secondes par unité.
- Fréquences d'échantillonnage : vibration et courant à 100 Hz, couple à 10 Hz, température à 1 Hz.
- Taux d'unités défectueuses : 20-30 %, réparti entre deux scénarios : dégradation de roulement (température et vibration corrélées) et déséquilibre de phase (courant, isolé).
- Le statut réel de chaque unité (saine/défectueuse, type de défaut) est stocké séparément des flux de mesures, dans un manifeste de vérité terrain dédié, jamais mélangé aux messages de capteurs.

## Pourquoi

Séparer la vérité terrain des mesures reproduit la contrainte réelle d'un pipeline de détection d'anomalie : le système ne doit pas connaître la réponse à l'avance. Mélanger les deux aurait rendu l'exercice de détection trivial et non représentatif d'un cas réel. Cette séparation permet également de calculer la précision et le rappel de la détection en Phase 3, en comparant a posteriori les résultats de Spark au manifeste, sans jamais l'exposer au traitement lui-même.

Un stade de test unique a été retenu plutôt qu'une simulation multi-stades (contrôles intermédiaires d'assemblage, étanchéité) car ces contrôles mesurent des grandeurs différentes des quatre capteurs déjà définis et nécessiteraient de nouveaux topics et schémas, hors périmètre budgété pour cette itération.

## Conséquences

- Le simulateur produit deux types de sorties distincts : les flux de mesures par capteur (un fichier JSON Lines par type, préfigurant les futurs topics Kafka de la Phase 2), et un manifeste de vérité terrain à usage d'évaluation uniquement.
- Toute évolution future vers un stade de test supplémentaire nécessitera un nouvel ADR, de nouveaux topics et un nouveau schéma de données.
- Six tests unitaires couvrent les deux signatures de défaut (amplitude de vibration, vitesse de montée en température, déséquilibre d'amplitude de phase) et la cohérence entre manifeste et mesures.
