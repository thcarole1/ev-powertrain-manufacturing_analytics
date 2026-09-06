import numpy as np

from simulator import motor_profiles as mp
from simulator.config import SimulationConfig
from simulator.generator import generate_unit


def test_manifest_defect_rate_is_close_to_configured_rate():
    config = SimulationConfig()
    rng = np.random.default_rng(0)
    n = 500
    defective_count = sum(
        1 for i in range(n) if generate_unit(f"unit_{i}", rng, config)[1]["defective"]
    )
    rate = defective_count / n
    assert config.defect_rate - 0.1 < rate < config.defect_rate + 0.1


def test_bearing_defect_produces_higher_vibration_amplitude_than_normal():
    config = SimulationConfig()
    rng_normal = np.random.default_rng(1)
    rng_defect = np.random.default_rng(1)

    _, vibration_normal = mp.generate_vibration(
        rng_normal, config.test_duration_s, config.vibration_hz, defective_bearing=False
    )
    _, vibration_defect = mp.generate_vibration(
        rng_defect, config.test_duration_s, config.vibration_hz, defective_bearing=True
    )

    assert np.std(vibration_defect) > np.std(vibration_normal) * 2


def test_bearing_defect_produces_faster_temperature_rise_than_normal():
    config = SimulationConfig()
    rng_normal = np.random.default_rng(1)
    rng_defect = np.random.default_rng(1)

    _, temperature_normal = mp.generate_temperature(
        rng_normal, config.test_duration_s, config.temperature_hz, defective_bearing=False
    )
    _, temperature_defect = mp.generate_temperature(
        rng_defect, config.test_duration_s, config.temperature_hz, defective_bearing=True
    )

    assert temperature_defect[-1] > temperature_normal[-1]


def test_phase_imbalance_defect_reduces_one_phase_amplitude():
    config = SimulationConfig()
    rng_normal = np.random.default_rng(2)
    rng_defect = np.random.default_rng(2)

    _, phases_normal = mp.generate_current_phases(
        rng_normal, config.test_duration_s, config.current_hz, defective_phase=False
    )
    _, phases_defect = mp.generate_current_phases(
        rng_defect, config.test_duration_s, config.current_hz, defective_phase=True
    )

    amplitude_normal = np.max(np.abs(phases_normal["B"]))
    amplitude_defect = np.max(np.abs(phases_defect["B"]))
    assert amplitude_defect < amplitude_normal * 0.85


def test_manifest_and_sensor_records_share_the_same_unit_id():
    config = SimulationConfig()
    rng = np.random.default_rng(3)
    records, manifest_entry = generate_unit("unit_00042", rng, config)

    for sensor_type, rows in records.items():
        assert all(row["unit_id"] == "unit_00042" for row in rows), sensor_type
    assert manifest_entry["unit_id"] == "unit_00042"


def test_healthy_unit_manifest_has_no_defect_type():
    config = SimulationConfig()
    rng = np.random.default_rng(4)
    found_healthy = False
    for i in range(50):
        _, manifest_entry = generate_unit(f"unit_{i}", rng, config)
        if not manifest_entry["defective"]:
            assert manifest_entry["defect_type"] == "none"
            found_healthy = True
    assert found_healthy
