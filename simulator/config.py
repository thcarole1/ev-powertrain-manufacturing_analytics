from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    """Paramètres du test électrique final, fixés par ADR-002."""

    test_duration_s: float = 30.0
    temperature_hz: float = 1.0
    torque_hz: float = 10.0
    vibration_hz: float = 100.0
    current_hz: float = 1000.0
    defect_rate: float = 0.25
    random_seed: int = 42


@dataclass(frozen=True)
class StreamingDemoConfig(SimulationConfig):
    """Fréquences allégées pour la démo streaming temps réel.

    Avec plusieurs unités simulées en parallèle (threading, donc soumises
    au GIL), les fréquences complètes du batch (jusqu'à 1000 Hz sur le
    courant) créaient un volume de messages trop élevé pour tenir dans le
    rythme réel prévu : des trous de silence supérieurs au gap de session
    (8s) fragmentaient artificiellement une même unité en plusieurs
    sessions distinctes. Ces fréquences restent largement suffisantes pour
    la détection (5 échantillons/cycle minimum, bien au-dessus du cas
    limite de Nyquist déjà corrigé) — seule la fidélité du signal brut est
    réduite, pas la capacité de détection.
    """

    vibration_hz: float = 50.0
    current_hz: float = 50.0
