"""Simulation « et si ? » : effet d'une variation de volume et de prix sur l'atteinte de l'objectif."""
import numpy as np


def projeter(ca_mensuel: list[float], objectif: float, variation_volume: float = 0.0,
             variation_prix: float = 0.0, mois_a_projeter: int = 3) -> dict:
    """
    ca_mensuel : historique du CA par mois (même unité que objectif, ex. M Ar).
    variation_volume, variation_prix : en pourcentage (ex. +10 = +10 %).
    Hypothèse : le rythme actuel = moyenne des 3 derniers mois ; le scénario le multiplie par
    (1 + volume) x (1 + prix). Le résultat est le CA cumulé à la fin de l'horizon.
    """
    y = np.asarray(ca_mensuel, dtype=float)
    if len(y) == 0:
        raise ValueError("Historique vide.")
    cumul = float(y.sum())
    rythme = float(np.mean(y[-3:]))
    facteur = (1 + variation_volume / 100) * (1 + variation_prix / 100)
    mensuel_scenario = rythme * facteur
    mensuel_base = rythme

    cumul_base = cumul + mensuel_base * mois_a_projeter
    cumul_scenario = cumul + mensuel_scenario * mois_a_projeter

    # Effort nécessaire pour atteindre l'objectif sur l'horizon
    requis_mensuel = (objectif - cumul) / mois_a_projeter if mois_a_projeter else 0.0
    hausse_requise = (requis_mensuel / rythme - 1) * 100 if rythme else float("inf")

    serie_base = np.concatenate([np.cumsum(y), cumul + mensuel_base * np.arange(1, mois_a_projeter + 1)])
    serie_scen = np.concatenate([np.cumsum(y), cumul + mensuel_scenario * np.arange(1, mois_a_projeter + 1)])
    return {
        "rythme_actuel": rythme,
        "mensuel_scenario": mensuel_scenario,
        "cumul_actuel": cumul,
        "cumul_base": cumul_base,
        "cumul_scenario": cumul_scenario,
        "gain_scenario": cumul_scenario - cumul_base,
        "taux_atteinte_base": cumul_base / objectif * 100 if objectif else None,
        "taux_atteinte_scenario": cumul_scenario / objectif * 100 if objectif else None,
        "hausse_requise_pct": hausse_requise,
        "serie_base": serie_base.tolist(),
        "serie_scenario": serie_scen.tolist(),
        "n_historique": len(y),
    }
