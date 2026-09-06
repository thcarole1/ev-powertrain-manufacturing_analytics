import json


class JsonlWriter:
    """Écrit des dictionnaires en JSON Lines, un par ligne."""

    def __init__(self, path):
        self._file = open(path, "w", encoding="utf-8")

    def write(self, record):
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_many(self, records):
        for record in records:
            self.write(record)

    def close(self):
        self._file.close()
