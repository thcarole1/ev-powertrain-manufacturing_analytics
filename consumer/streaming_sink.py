"""Sink foreachBatch générique, réutilisable par les trois requêtes streaming.

Écrit en JSON Lines plutôt que toPandas() — évite l'incompatibilité
PySpark 3.5.6 / Python 3.12 déjà rencontrée sur distutils.
"""

import json
import threading

_locks_guard = threading.Lock()
_locks = {}


def _get_lock(path):
    with _locks_guard:
        if path not in _locks:
            _locks[path] = threading.Lock()
        return _locks[path]


def append_batch_to_jsonl(path):
    """Retourne une fonction foreachBatch qui ajoute chaque ligne d'un micro-batch au fichier."""
    lock = _get_lock(path)

    def write_batch(batch_df, batch_id):
        rows = batch_df.collect()
        if not rows:
            return
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row.asDict(), ensure_ascii=False) + "\n")

    return write_batch
