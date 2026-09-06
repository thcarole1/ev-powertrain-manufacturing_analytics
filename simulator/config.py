from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    """Paramètres du test électrique final, fixés par ADR-002."""

    test_duration_s: float = 30.0
    temperature_hz: float = 1.0
    torque_hz: float = 10.0
    vibration_hz: float = 100.0
    current_hz: float = 100.0
    defect_rate: float = 0.25
    random_seed: int = 42
