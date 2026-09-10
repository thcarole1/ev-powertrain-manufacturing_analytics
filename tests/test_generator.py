import numpy as np

from simulator import motor_profiles as mp
from simulator.config import SimulationConfig, StreamingDemoConfig
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


def test_vibration_amplitude_is_not_collapsed_by_sampling_alignment():
    """Non-régression : à 50 Hz sur 100 Hz d'échantillonnage sans déphasage,
    chaque échantillon tombait exactement sur un passage à zéro du signal,
    effondrant l'amplitude mesurée à un niveau de pur bruit quelle que soit
    l'amplitude réelle configurée. Vérifie que ce n'est plus le cas.
    """
    config = SimulationConfig()
    rng = np.random.default_rng(123)
    _, vibration_normal = mp.generate_vibration(
        rng, config.test_duration_s, config.vibration_hz, defective_bearing=False
    )
    measured_amplitude = np.max(np.abs(vibration_normal))
    assert measured_amplitude > 0.5  # amplitude réelle configurée : 0.8


def test_current_phase_a_amplitude_is_not_collapsed_by_sampling_alignment():
    """Non-régression : la phase A (sans déphasage) tombait systématiquement
    sur les passages à zéro à 100 Hz pour un signal à 50 Hz, effondrant son
    amplitude mesurée à ~0.3 A au lieu de ~10 A — cassant le ratio de
    déséquilibre pour toutes les unités, saines comme défectueuses.
    """
    config = SimulationConfig()
    rng = np.random.default_rng(456)
    _, phases_normal = mp.generate_current_phases(
        rng, config.test_duration_s, config.current_hz, defective_phase=False
    )
    measured_amplitude_a = np.max(np.abs(phases_normal["A"]))
    assert measured_amplitude_a > 8.0  # amplitude réelle configurée : 10.0


def test_streaming_demo_current_amplitude_is_not_collapsed_on_any_phase():
    """Non-régression sur un second incident : StreamingDemoConfig.current_hz
    avait été fixé à 50 Hz, exactement égal à la fréquence du signal
    (1 échantillon/cycle) — pire que le cas limite de Nyquist déjà corrigé
    ci-dessus. Toutes les unités, saines comme défectueuses, affichaient un
    ratio de déséquilibre faussement bas. Vérifie les trois phases, pas
    seulement A (le déphasage aléatoire fait varier quelle phase s'effondre
    d'une unité à l'autre).
    """
    config = StreamingDemoConfig()
    rng = np.random.default_rng(789)
    _, phases_normal = mp.generate_current_phases(
        rng, config.test_duration_s, config.current_hz, defective_phase=False
    )
    for phase_name, values in phases_normal.items():
        amplitude = np.max(np.abs(values))
        assert amplitude > 8.0, f"phase {phase_name} : amplitude effondrée à {amplitude:.2f}"
