import argparse
from pathlib import Path

import numpy as np

from simulator.config import SimulationConfig
from simulator.generator import generate_unit, new_unit_id
from simulator.kafka_producer import build_producer, stream_unit_records
from simulator.writer import JsonlWriter


def main():
    parser = argparse.ArgumentParser(description="Diffuse des unités simulées vers Kafka local")
    parser.add_argument("--num-units", type=int, default=20)
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092")
    parser.add_argument("--manifest-path", type=str, default="data/output/units-manifest.jsonl")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Graine du générateur aléatoire. Contrôle TOUTE la séquence : "
            "quelles unités sont défectueuses, quel défaut, et toutes les valeurs "
            "de capteurs. Réutiliser le même seed régénère exactement les mêmes "
            "unit_id avec les mêmes données — utile pour reproduire un envoi à "
            "l'identique, mais provoque des unit_id dupliqués si le topic contient "
            "déjà un envoi précédent avec ce seed. Omettre ce paramètre (défaut) "
            "tire une graine aléatoire différente à chaque exécution."
        ),
    )
    args = parser.parse_args()

    config = SimulationConfig()
    rng = np.random.default_rng(args.seed)
    producer = build_producer(args.bootstrap_servers)

    manifest_path = Path(args.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_writer = JsonlWriter(manifest_path)

    for i in range(args.num_units):
        unit_id = new_unit_id()
        records, manifest_entry = generate_unit(unit_id, rng, config)
        stream_unit_records(producer, unit_id, records)
        manifest_writer.write(manifest_entry)
        print(f"Unité {unit_id} envoyée à Kafka (défectueuse : {manifest_entry['defective']})")

    producer.flush()
    producer.close()
    manifest_writer.close()
    print(f"{args.num_units} unités envoyées. Manifeste écrit dans {manifest_path}")


if __name__ == "__main__":
    main()
