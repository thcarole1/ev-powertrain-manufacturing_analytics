"""Génère N unités testées en fin de ligne, avec une proportion de défauts.

Sorties (ADR-002) :
- un fichier JSON Lines par type de capteur (préfigure les futurs topics Kafka)
- un manifeste séparé de vérité terrain (jamais mélangé aux mesures)
"""

import argparse
import uuid
from pathlib import Path

import numpy as np

from . import motor_profiles as mp
from .config import SimulationConfig
from .writer import JsonlWriter

DEFECT_NONE = "none"
DEFECT_BEARING = "bearing"
DEFECT_PHASE = "phase_imbalance"


def new_unit_id():
    """Identifiant globalement unique, valable au-delà d'une seule exécution.

    Un compteur remis à zéro à chaque lancement (unit_00000, unit_00001...)
    entrerait en collision avec les unités des exécutions précédentes encore
    présentes dans Kafka — celui-ci ne collisionne jamais, sans coordination
    entre exécutions ni entre plusieurs stations de test en parallèle.
    """
    return f"unit_{uuid.uuid4().hex[:8]}"


def assign_defect(rng, defect_rate):
    if rng.random() >= defect_rate:
        return DEFECT_NONE
    return rng.choice([DEFECT_BEARING, DEFECT_PHASE])


def generate_unit(unit_id, rng, config):
    """Génère les mesures et le statut d'une unité testée.

    Retourne (records, manifest_entry) :
    - records : dict {type_capteur: [mesures]}
    - manifest_entry : dict de vérité terrain pour cette unité
    """
    defect = assign_defect(rng, config.defect_rate)
    defective_bearing = defect == DEFECT_BEARING
    defective_phase = defect == DEFECT_PHASE

    t_temp, temperature = mp.generate_temperature(
        rng, config.test_duration_s, config.temperature_hz, defective_bearing
    )
    t_vib, vibration = mp.generate_vibration(
        rng, config.test_duration_s, config.vibration_hz, defective_bearing
    )
    t_torque, torque = mp.generate_torque(rng, config.test_duration_s, config.torque_hz)
    t_current, phases = mp.generate_current_phases(
        rng, config.test_duration_s, config.current_hz, defective_phase
    )

    records = {
        "temperature": [
            {"unit_id": unit_id, "t": float(ti), "value": float(v)} for ti, v in zip(t_temp, temperature)
        ],
        "vibration": [
            {"unit_id": unit_id, "t": float(ti), "value": float(v)} for ti, v in zip(t_vib, vibration)
        ],
        "torque": [
            {"unit_id": unit_id, "t": float(ti), "value": float(v)} for ti, v in zip(t_torque, torque)
        ],
        "current": (
            [{"unit_id": unit_id, "t": float(ti), "phase": "A", "value": float(v)} for ti, v in zip(t_current, phases["A"])]
            + [{"unit_id": unit_id, "t": float(ti), "phase": "B", "value": float(v)} for ti, v in zip(t_current, phases["B"])]
            + [{"unit_id": unit_id, "t": float(ti), "phase": "C", "value": float(v)} for ti, v in zip(t_current, phases["C"])]
        ),
    }
    manifest_entry = {"unit_id": unit_id, "defective": defect != DEFECT_NONE, "defect_type": defect}
    return records, manifest_entry


def run(num_units, output_dir, config, seed=None):
    rng = np.random.default_rng(seed if seed is not None else config.random_seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    writers = {
        "temperature": JsonlWriter(output_dir / "sensor-temperature.jsonl"),
        "vibration": JsonlWriter(output_dir / "sensor-vibration.jsonl"),
        "torque": JsonlWriter(output_dir / "sensor-torque.jsonl"),
        "current": JsonlWriter(output_dir / "sensor-current.jsonl"),
    }
    manifest_writer = JsonlWriter(output_dir / "units-manifest.jsonl")

    for i in range(num_units):
        unit_id = new_unit_id()
        records, manifest_entry = generate_unit(unit_id, rng, config)
        for sensor_type, rows in records.items():
            writers[sensor_type].write_many(rows)
        manifest_writer.write(manifest_entry)

    for writer in writers.values():
        writer.close()
    manifest_writer.close()


def main():
    parser = argparse.ArgumentParser(description="Simulateur de test électrique final pour moteurs PMSM")
    parser.add_argument("--num-units", type=int, default=100)
    parser.add_argument("--output-dir", type=str, default="data/output")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Graine du générateur aléatoire. Contrôle TOUTE la séquence : "
            "quelles unités sont défectueuses, quel défaut, et toutes les valeurs "
            "de capteurs. Réutiliser le même seed régénère exactement le même jeu "
            "de données. Omettre ce paramètre (défaut) tire une graine aléatoire "
            "différente à chaque exécution."
        ),
    )
    args = parser.parse_args()

    config = SimulationConfig()
    run(args.num_units, args.output_dir, config, seed=args.seed)
    print(f"Généré {args.num_units} unités dans {args.output_dir}")


if __name__ == "__main__":
    main()
