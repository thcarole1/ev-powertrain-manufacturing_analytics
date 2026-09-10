# ADR-004 — Architecture découplée pour la détection streaming à 3 capteurs

## Contexte

ADR-003 valide la détection streaming sur un seul capteur (vibration). Cet ADR documente l'extension aux trois capteurs (vibration, température, courant) nécessaires à la classification complète, ainsi que les incidents rencontrés — significativement plus nombreux que pour un seul capteur.

## Décision

- **Jointure stream-stream native abandonnée**, au profit d'une architecture découplée :
  - Trois requêtes streaming indépendantes (une par capteur), chacune réutilisant le mécanisme déjà validé (`session_window` + watermark), écrivent leurs résultats finalisés dans un fichier JSON Lines via `foreachBatch`.
  - Un job batch séparé, relancé à la demande, lit les trois fichiers, déduplique, joint sur `unit_id` et classifie — en jointure batch classique, sans les subtilités d'une jointure stream-stream.
- **Déduplication systématique avant jointure**, gardant toujours la valeur la plus défavorable entre fragments dupliqués d'une même unité (maximum pour vibration/température, minimum pour le ratio de courant) — jamais une moyenne, qui masquerait un défaut réel capturé par un seul fragment.
- **`flush()`/`close()` du producteur bornés dans le temps** (60s / 30s), avec avertissement explicite en cas de dépassement plutôt qu'un blocage silencieux.

## Pourquoi

**Abandon de la jointure stream-stream native** : une requête chaînant trois agrégations par session et deux jointures stream-stream (cinq opérations avec état au total) se bloquait après un nombre fini de micro-batchs, sans erreur ni job actif visible dans l'interface Spark — un état confirmé par l'observation directe (`http://localhost:4040`), pas supposé. Une première hypothèse (watermark ambiguë entre les deux colonnes de temps après la première jointure) a été corrigée sans effet sur le blocage, indiquant une cause plus profonde que ce qui a pu être diagnostiqué dans le temps imparti — probablement une limite réelle de Spark sur ce type d'assemblage, non documentée clairement. Continuer à chercher la cause exacte présentait un rapport coût/bénéfice défavorable face à une alternative connue pour fonctionner : chaque brique (streaming à un capteur, jointure batch) était déjà individuellement validée.

**Déduplication plutôt que suppression complète de la fragmentation** : malgré l'élargissement du gap de session (8s → 20s, voir Incidents), une fragmentation résiduelle subsiste à grande échelle (50 unités), probablement liée au simulateur Python multi-thread (GIL) plutôt qu'à Kafka/Spark eux-mêmes. Plutôt que de poursuivre indéfiniment la chasse à une élimination totale, un filet de sécurité déterministe (toujours la valeur la plus suspecte) absorbe la fragmentation résiduelle sans jamais masquer un vrai défaut.

## Incidents

### Blocage de la jointure stream-stream (non résolu, contournement architectural)

Voir "Pourquoi" ci-dessus. La fonction `join_three_sensors()` et le script associé sont conservés dans le code, documentés comme abandonnés, avec leurs tests batch (qui passent) — utile pour illustrer qu'une logique correcte en isolation peut échouer une fois confrontée à un vrai flux streaming, une limite réelle des tests unitaires sur du code avec état.

### Repliement de spectre réintroduit sur le courant de la démo streaming

En allégeant `StreamingDemoConfig.current_hz` de 1000 à 50 Hz pour résoudre un problème de volume (voir ADR-003), le nouveau taux égalait exactement la fréquence du signal simulé (50 Hz) — un échantillon par cycle, pire que le cas limite de Nyquist déjà rencontré. Toutes les unités, saines comme défectueuses, affichaient un ratio de déséquilibre faussement bas. Le volume avait été vérifié, pas la contrainte de Nyquist sur la nouvelle fréquence. Corrigé à 400 Hz (8 échantillons/cycle).

### Fragmentation de session à grande échelle (50 unités)

Un gap de session de 8 secondes, suffisant à 10 unités, ne l'était plus à 50 — la durée totale du run (8-10 minutes) augmente la probabilité qu'un ralentissement passager du producteur dépasse le seuil au moins une fois. Élargi à 20 secondes (watermark à 30s), réduisant la fragmentation sans l'éliminer totalement — d'où la déduplication en filet de sécurité.

### `producer.flush()` bloqué indéfiniment sur un très gros volume

Sur un run à 50 unités (~1,9 million de messages), le producteur restait bloqué plus de 16 minutes sans qu'aucune nouvelle donnée n'atteigne Kafka — confirmé par un `Input Rate` resté strictement à zéro sur l'interface Spark. Cause exacte non identifiée avec certitude (comportement de `kafka-python` sous forte charge concurrente, non documenté clairement) ; contournée en bornant `flush()`/`close()` dans le temps plutôt qu'en cherchant à l'éliminer.

## Conséquences

- Deux étapes séparées (streaming continu + jointure batch à la demande) plutôt qu'un pipeline unique de bout en bout — moins élégant, mais chaque brique reste individuellement déboguable.
- La déduplication "valeur la plus défavorable" est un compromis assumé : elle peut légèrement sur-estimer le taux de détection dans un cas limite où un fragment capte une valeur extrême par bruit plutôt que par vrai défaut — acceptable pour cette échelle de démonstration, à revisiter si le taux de faux positifs devenait un problème réel.
- Une poignée d'unités par run (2-3 sur 50) restent incomplètes si le pipeline streaming est arrêté manuellement avant que leurs toutes dernières sessions ne se finalisent — comportement attendu, pas un bug, propre à l'arrêt manuel d'un flux conçu pour tourner en continu.
- Validé à 50 unités : 14/14 unités défectueuses détectées, 0 faux positif sur les 36 unités saines.
