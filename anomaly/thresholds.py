from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionThresholds:
    """Seuils calibrés sur les paramètres normaux/défectueux de motor_profiles.py.

    En conditions réelles, ces seuils se calibreraient sur des données
    labellisées historiques, pas sur la connaissance du générateur — ici,
    le simulateur nous donne cette connaissance directement, ce qui est
    acceptable pour valider que le pipeline de détection fonctionne, mais
    ne remplace pas une vraie calibration en Phase 3 avancée.
    """

    vibration_std_max_normal: float = 1.5
    temperature_rise_max_normal: float = 25.0
    current_imbalance_ratio_min_normal: float = 0.85
