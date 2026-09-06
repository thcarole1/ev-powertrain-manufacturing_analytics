"""Génération des signaux capteurs pour un moteur PMSM en test électrique final.

Chaque fonction retourne (t, valeurs) pour un profil normal ou défectueux.
Les paramètres physiques (amplitudes, fréquences, bruit) sont volontairement
simples : l'objectif est une signature détectable, pas un modèle électromagnétique
fidèle.
"""

import numpy as np


def generate_temperature(rng, duration_s, hz, defective_bearing):
    """Température du carter moteur pendant le test.

    Un roulement mal assemblé génère plus de friction : montée en
    température plus rapide dès le début du test, pas une dérive lente.
    """
    n = int(duration_s * hz)
    t = np.linspace(0, duration_s, n, endpoint=False)
    ambient = 25.0
    if defective_bearing:
        rise_rate = 1.2
        noise_std = 0.4
    else:
        rise_rate = 0.5
        noise_std = 0.2
    temperature = ambient + rise_rate * t + rng.normal(0, noise_std, n)
    return t, temperature


def generate_vibration(rng, duration_s, hz, defective_bearing):
    """Vibration radiale pendant le test.

    Un roulement mal assemblé produit une amplitude vibratoire nettement
    plus élevée que la normale, présente dès le début du test.
    """
    n = int(duration_s * hz)
    t = np.linspace(0, duration_s, n, endpoint=False)
    base_freq_hz = 50.0
    if defective_bearing:
        amplitude = 4.0
        noise_std = 0.5
    else:
        amplitude = 0.8
        noise_std = 0.15
    signal = amplitude * np.sin(2 * np.pi * base_freq_hz * t) + rng.normal(0, noise_std, n)
    return t, signal


def generate_torque(rng, duration_s, hz):
    """Couple moteur pendant le test.

    Non utilisé par les deux scénarios de défaut retenus pour l'instant,
    conservé pour rester cohérent avec le brief initial du projet.
    """
    n = int(duration_s * hz)
    t = np.linspace(0, duration_s, n, endpoint=False)
    nominal_nm = 15.0
    noise_std = 0.3
    ripple = 0.5 * np.sin(2 * np.pi * 6.0 * t)
    torque = nominal_nm + ripple + rng.normal(0, noise_std, n)
    return t, torque


def generate_current_phases(rng, duration_s, hz, defective_phase):
    """Courant sur les trois phases pendant le test.

    Un défaut de connexion/bobinage réduit l'amplitude d'une phase par
    rapport aux deux autres : déséquilibre mesurable dès le début du test.
    """
    n = int(duration_s * hz)
    t = np.linspace(0, duration_s, n, endpoint=False)
    nominal_amp_a = 10.0
    supply_freq_hz = 50.0
    noise_std = 0.1

    phase_a = nominal_amp_a * np.sin(2 * np.pi * supply_freq_hz * t) + rng.normal(0, noise_std, n)

    amp_b = nominal_amp_a * (0.65 if defective_phase else 1.0)
    phase_b = amp_b * np.sin(2 * np.pi * supply_freq_hz * t + 2 * np.pi / 3) + rng.normal(0, noise_std, n)

    phase_c = nominal_amp_a * np.sin(2 * np.pi * supply_freq_hz * t + 4 * np.pi / 3) + rng.normal(0, noise_std, n)

    return t, {"A": phase_a, "B": phase_b, "C": phase_c}
