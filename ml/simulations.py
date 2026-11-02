"""Simulations : marge, performance d'un agent et risque sur l'objectif.

Les fonctions de calcul (simuler_*) n'accèdent pas à la base : elles sont testables seules.
Les fonctions historique_* et objectifs_* lisent la base (import paresseux de app.db).
Toutes les valeurs monétaires sont exprimées dans la même unité (ex. M Ar).
"""
import numpy as np


# ---------------------------------------------------------------------------
# 1. Simulation de marge
# ---------------------------------------------------------------------------
def simuler_marge(ca_mensuel, taux_marge_pct, variation_prix=0.0, variation_volume=0.0,
                  mois_a_projeter=3):
    """
    ca_mensuel : historique du CA par mois.
    taux_marge_pct : taux de marge actuel en % du CA (marge / CA), ex. 20.
    variation_prix, variation_volume : en %, ex. +10 = +10 %.

    Hypothèses :
    - le rythme actuel est la moyenne des 3 derniers mois ;
    - le coût unitaire ne change pas quand le prix varie ;
    - une variation de volume multiplie le CA et la marge par le même facteur.

    Avec R = CA mensuel actuel, m = taux de marge, p = variation de prix, v = variation de volume :
      CA scénario   = R (1 + v)(1 + p)
      marge scénario = R (1 + v)(m + p)
      taux de marge scénario = (m + p) / (1 + p)
    """
    y = np.asarray(ca_mensuel, dtype=float)
    if len(y) == 0:
        raise ValueError("Historique vide.")
    if not 0 < taux_marge_pct < 100:
        raise ValueError("Le taux de marge doit être compris entre 0 et 100 %.")
    h = int(mois_a_projeter)
    if h < 1:
        raise ValueError("L'horizon doit être d'au moins 1 mois.")

    m = taux_marge_pct / 100
    p = variation_prix / 100
    v = variation_volume / 100
    if p <= -1 or v <= -1:
        raise ValueError("Une variation ne peut pas être inférieure à -100 %.")

    rythme = float(np.mean(y[-3:]))
    ca_base_mensuel = rythme
    ca_scen_mensuel = rythme * (1 + v) * (1 + p)
    marge_base_mensuelle = rythme * m
    marge_scen_mensuelle = rythme * (1 + v) * (m + p)

    marge_base = marge_base_mensuelle * h
    marge_scen = marge_scen_mensuelle * h
    taux_scen = (m + p) / (1 + p) * 100

    serie_base = [marge_base_mensuelle * i for i in range(1, h + 1)]
    serie_scen = [marge_scen_mensuelle * i for i in range(1, h + 1)]

    return {
        "rythme_actuel": rythme,
        "ca_base_mensuel": ca_base_mensuel,
        "ca_scenario_mensuel": ca_scen_mensuel,
        "ca_scenario_horizon": ca_scen_mensuel * h,
        "marge_base_horizon": marge_base,
        "marge_scenario_horizon": marge_scen,
        "gain_marge": marge_scen - marge_base,
        "taux_marge_actuel": taux_marge_pct,
        "taux_marge_scenario": taux_scen,
        # Baisse de prix qui annule la marge unitaire : au-delà, chaque vente fait perdre de l'argent.
        "prix_seuil_pct": -taux_marge_pct,
        "serie_marge_base": serie_base,
        "serie_marge_scenario": serie_scen,
    }


# ---------------------------------------------------------------------------
# 2. Simulation de la performance d'un agent
# ---------------------------------------------------------------------------
def simuler_agent(ventes_par_agent, agent, variation_pct, objectif_agence=0.0, objectif_agent=0.0,
                  mois_a_projeter=3):
    """
    ventes_par_agent : {nom_agent: [CA par mois]}, toutes les séries de même longueur, dans l'ordre
                       chronologique (un mois sans vente vaut 0).
    agent : nom de l'agent dont on fait varier la performance.
    variation_pct : variation du rythme mensuel de cet agent, en % (ex. +20).

    L'agence est la somme des agents. Le rythme de chacun est la moyenne de ses 3 derniers mois.
    """
    if not ventes_par_agent:
        raise ValueError("Aucune vente pour cette agence.")
    if agent not in ventes_par_agent:
        raise ValueError(f"Agent inconnu : {agent}")
    series = {nom: np.asarray(v, dtype=float) for nom, v in ventes_par_agent.items()}
    longueurs = {len(v) for v in series.values()}
    if len(longueurs) != 1:
        raise ValueError("Les séries des agents doivent avoir la même longueur.")
    n = longueurs.pop()
    if n < 3:
        raise ValueError("Historique insuffisant (3 mois minimum).")
    h = int(mois_a_projeter)
    if h < 1:
        raise ValueError("L'horizon doit être d'au moins 1 mois.")
    if variation_pct <= -100:
        raise ValueError("Une variation ne peut pas être inférieure à -100 %.")

    y_agence = np.sum(list(series.values()), axis=0)
    y_agent = series[agent]
    rythme_agence = float(np.mean(y_agence[-3:]))
    rythme_agent = float(np.mean(y_agent[-3:]))
    var = variation_pct / 100
    delta_mensuel = rythme_agent * var

    cumul_hist_agence = float(y_agence.sum())
    cumul_base = cumul_hist_agence + rythme_agence * h
    cumul_scen = cumul_hist_agence + (rythme_agence + delta_mensuel) * h

    cumul_hist_agent = float(y_agent.sum())
    agent_base = cumul_hist_agent + rythme_agent * h
    agent_scen = cumul_hist_agent + rythme_agent * (1 + var) * h

    def taux(valeur, objectif):
        return valeur / objectif * 100 if objectif else None

    cumsum_hist = np.cumsum(y_agence)
    pas = np.arange(1, h + 1)
    serie_base = np.concatenate([cumsum_hist, cumul_hist_agence + rythme_agence * pas])
    serie_scen = np.concatenate([cumsum_hist, cumul_hist_agence + (rythme_agence + delta_mensuel) * pas])

    return {
        "agent": agent,
        "rythme_agence": rythme_agence,
        "rythme_agent": rythme_agent,
        "part_agent_pct": rythme_agent / rythme_agence * 100 if rythme_agence else None,
        "cumul_agence_base": cumul_base,
        "cumul_agence_scenario": cumul_scen,
        "gain_agence": cumul_scen - cumul_base,
        "taux_atteinte_agence_base": taux(cumul_base, objectif_agence),
        "taux_atteinte_agence_scenario": taux(cumul_scen, objectif_agence),
        "cumul_agent_base": agent_base,
        "cumul_agent_scenario": agent_scen,
        "taux_atteinte_agent_base": taux(agent_base, objectif_agent),
        "taux_atteinte_agent_scenario": taux(agent_scen, objectif_agent),
        "serie_base": serie_base.tolist(),
        "serie_scenario": serie_scen.tolist(),
        "n_historique": n,
    }


# ---------------------------------------------------------------------------
# 3. Simulation de risque (Monte Carlo)
# ---------------------------------------------------------------------------
def simuler_risque(ca_mensuel, mois_a_projeter=3, objectif=0.0, n_tirages=10000, seed=42):
    """
    Tire au hasard des trajectoires de CA et donne une fourchette probable.

    Hypothèses :
    - le niveau de chaque mois projeté est le rythme actuel (moyenne des 3 derniers mois) ;
    - la variabilité est la dispersion relative des 6 derniers mois, plafonnée à 100 % ;
    - les mois sont indépendants entre eux (pas de tendance modélisée) ;
    - le tirage est reproductible grâce à la graine (seed).
    """
    y = np.asarray(ca_mensuel, dtype=float)
    if len(y) < 3:
        raise ValueError("Historique insuffisant (3 mois minimum).")
    h = int(mois_a_projeter)
    if h < 1:
        raise ValueError("L'horizon doit être d'au moins 1 mois.")

    rythme = float(np.mean(y[-3:]))
    recent = y[-6:]
    moyenne_recente = float(np.mean(recent))
    if moyenne_recente > 0 and len(recent) > 1:
        sigma = min(float(np.std(recent, ddof=1)) / moyenne_recente, 1.0)
    else:
        sigma = 0.0

    total_hist = float(y.sum())
    cumul_hist = np.cumsum(y)

    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, size=(n_tirages, h))
    mensuel = np.maximum(0.0, rythme * (1 + eps))
    trajectoires = total_hist + np.cumsum(mensuel, axis=1)     # cumul total après chaque mois projeté
    finaux = trajectoires[:, -1]

    p10, p50, p90 = (float(v) for v in np.percentile(finaux, [10, 50, 90]))
    bande_basse = np.percentile(trajectoires, 10, axis=0)
    bande_mediane = np.percentile(trajectoires, 50, axis=0)
    bande_haute = np.percentile(trajectoires, 90, axis=0)

    proba = float(np.mean(finaux >= objectif) * 100) if objectif and objectif > 0 else None
    comptes, bords = np.histogram(finaux, bins=30)

    return {
        "rythme_actuel": rythme,
        "volatilite_pct": sigma * 100,
        "cumul_actuel": total_hist,
        "cumul_p10": p10,
        "cumul_p50": p50,
        "cumul_p90": p90,
        "cumul_moyen": float(np.mean(finaux)),
        "probabilite_objectif_pct": proba,
        "serie_p10": np.concatenate([cumul_hist, bande_basse]).tolist(),
        "serie_mediane": np.concatenate([cumul_hist, bande_mediane]).tolist(),
        "serie_p90": np.concatenate([cumul_hist, bande_haute]).tolist(),
        "histogramme": comptes.tolist(),
        "bords_histogramme": bords.tolist(),
        "n_tirages": n_tirages,
        "n_historique": len(y),
    }


# ---------------------------------------------------------------------------
# Lecture de la base (import paresseux pour garder les fonctions ci-dessus indépendantes)
# ---------------------------------------------------------------------------
def historique_mensuel_par_agent(agence: str) -> dict:
    """{agent: [CA mensuel en M Ar]} pour une agence, sur les mois alignés."""
    import pandas as pd
    from sqlalchemy import text
    from app.db import engine

    requete = text("""
        SELECT dd.annee, dd.mois, ag.agent, SUM(f.montant) AS ca
        FROM fait_vente f
        JOIN dim_date dd ON dd.id_temps = f.id_temps
        JOIN dim_agent ag ON ag.id_agent = f.id_agent
        JOIN dim_agence da ON da.id_agence = f.id_agence
        WHERE da.agence = :agence
        GROUP BY dd.annee, dd.mois, ag.agent
        ORDER BY dd.annee, dd.mois
    """)
    df = pd.read_sql(requete, engine, params={"agence": agence})
    if df.empty:
        return {}
    df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
    piv = df.pivot_table(index="periode", columns="agent", values="ca", aggfunc="sum").fillna(0) / 1e6
    piv = piv.sort_index()
    return {agent: piv[agent].tolist() for agent in piv.columns}


def objectifs_agents(agence: str) -> dict:
    """{agent: objectif en M Ar} pour une agence."""
    import pandas as pd
    from sqlalchemy import text
    from app.db import engine

    df = pd.read_sql(
        text("""SELECT ag.agent, COALESCE(ag.objectif, 0) AS objectif
                FROM dim_agent ag JOIN dim_agence da ON da.id_agence = ag.id_agence
                WHERE da.agence = :agence"""),
        engine, params={"agence": agence})
    return {r.agent: float(r.objectif) / 1e6 for r in df.itertuples()}
