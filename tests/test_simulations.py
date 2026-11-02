import numpy as np
import pytest

from ml.simulations import simuler_agent, simuler_marge, simuler_risque

HISTO = [100.0, 120.0, 110.0, 130.0, 140.0, 150.0]   # rythme des 3 derniers mois = 140


# ---------- Marge ----------

def test_marge_sans_variation_reste_identique():
    r = simuler_marge(HISTO, 20, 0, 0, 3)
    assert r["marge_scenario_horizon"] == pytest.approx(r["marge_base_horizon"])
    assert r["gain_marge"] == pytest.approx(0)
    assert r["taux_marge_scenario"] == pytest.approx(20)


def test_marge_hausse_de_prix_augmente_le_taux():
    r = simuler_marge(HISTO, 20, variation_prix=10, mois_a_projeter=3)
    # taux = (0.20 + 0.10) / 1.10
    assert r["taux_marge_scenario"] == pytest.approx(0.30 / 1.10 * 100)
    assert r["gain_marge"] > 0


def test_marge_hausse_de_volume_multiplie_la_marge():
    r = simuler_marge(HISTO, 20, variation_volume=10, mois_a_projeter=3)
    assert r["marge_scenario_horizon"] == pytest.approx(r["marge_base_horizon"] * 1.10)
    assert r["taux_marge_scenario"] == pytest.approx(20)   # le volume ne change pas le taux


def test_marge_baisse_de_prix_au_seuil_annule_la_marge():
    r = simuler_marge(HISTO, 20, variation_prix=-20, mois_a_projeter=3)
    assert r["prix_seuil_pct"] == -20
    assert r["marge_scenario_horizon"] == pytest.approx(0, abs=1e-9)


def test_marge_taux_invalide_refuse():
    with pytest.raises(ValueError):
        simuler_marge(HISTO, 0)
    with pytest.raises(ValueError):
        simuler_marge(HISTO, 100)


def test_marge_variation_inferieure_a_moins_cent_refusee():
    with pytest.raises(ValueError):
        simuler_marge(HISTO, 20, variation_volume=-100)


def test_marge_series_de_longueur_horizon():
    r = simuler_marge(HISTO, 20, mois_a_projeter=5)
    assert len(r["serie_marge_base"]) == 5 and len(r["serie_marge_scenario"]) == 5


# ---------- Agent ----------

AGENTS = {
    "Rakoto": [50.0, 60.0, 55.0, 70.0, 80.0, 90.0],    # rythme 80
    "Rabe":   [50.0, 60.0, 55.0, 60.0, 60.0, 60.0],    # rythme 60
}


def test_agent_sans_variation_pas_de_gain():
    r = simuler_agent(AGENTS, "Rakoto", 0, objectif_agence=1000, objectif_agent=500)
    assert r["gain_agence"] == pytest.approx(0)
    assert r["cumul_agence_scenario"] == pytest.approx(r["cumul_agence_base"])


def test_agent_hausse_de_performance_gain_egal_variation_fois_rythme_fois_horizon():
    r = simuler_agent(AGENTS, "Rakoto", 25, objectif_agence=1000, mois_a_projeter=3)
    assert r["gain_agence"] == pytest.approx(0.25 * 80 * 3)
    assert r["cumul_agent_scenario"] - r["cumul_agent_base"] == pytest.approx(0.25 * 80 * 3)


def test_agent_part_et_taux_atteinte():
    r = simuler_agent(AGENTS, "Rakoto", 0, objectif_agence=1000, objectif_agent=0)
    assert r["part_agent_pct"] == pytest.approx(80 / 140 * 100)
    assert r["taux_atteinte_agent_base"] is None            # pas d'objectif agent
    assert r["taux_atteinte_agence_base"] == pytest.approx(r["cumul_agence_base"] / 1000 * 100)


def test_agent_inconnu_refuse():
    with pytest.raises(ValueError):
        simuler_agent(AGENTS, "Inconnu", 10)


def test_agent_series_de_longueurs_differentes_refusees():
    with pytest.raises(ValueError):
        simuler_agent({"A": [1, 2, 3, 4], "B": [1, 2, 3]}, "A", 10)


def test_agent_historique_trop_court():
    with pytest.raises(ValueError):
        simuler_agent({"A": [1.0, 2.0]}, "A", 10)


def test_agent_serie_horizon():
    r = simuler_agent(AGENTS, "Rabe", 10, mois_a_projeter=4)
    assert len(r["serie_base"]) == len(AGENTS["Rabe"]) + 4


# ---------- Risque ----------

def test_risque_historique_constant_donne_une_fourchette_nulle():
    r = simuler_risque([100.0] * 6, mois_a_projeter=3, objectif=0)
    assert r["volatilite_pct"] == pytest.approx(0)
    assert r["cumul_p10"] == pytest.approx(600 + 300)
    assert r["cumul_p50"] == pytest.approx(900)
    assert r["cumul_p90"] == pytest.approx(900)


def test_risque_fourchette_ordonnee():
    r = simuler_risque(HISTO, mois_a_projeter=3, objectif=0)
    assert r["cumul_p10"] <= r["cumul_p50"] <= r["cumul_p90"]


def test_risque_probabilite_objectif_extremes():
    tres_haut = simuler_risque(HISTO, objectif=10_000)
    assert tres_haut["probabilite_objectif_pct"] == 0
    tres_bas = simuler_risque(HISTO, objectif=1)
    assert tres_bas["probabilite_objectif_pct"] == 100
    sans_objectif = simuler_risque(HISTO, objectif=0)
    assert sans_objectif["probabilite_objectif_pct"] is None


def test_risque_reproductible_avec_la_graine():
    a = simuler_risque(HISTO, seed=7)
    b = simuler_risque(HISTO, seed=7)
    assert a["cumul_p50"] == b["cumul_p50"]


def test_risque_longueurs_et_histogramme():
    r = simuler_risque(HISTO, mois_a_projeter=4, n_tirages=2000)
    n = len(HISTO)
    assert len(r["serie_p10"]) == n + 4 == len(r["serie_p90"]) == len(r["serie_mediane"])
    assert sum(r["histogramme"]) == 2000
    assert len(r["bords_histogramme"]) == len(r["histogramme"]) + 1


def test_risque_historique_insuffisant():
    with pytest.raises(ValueError):
        simuler_risque([1.0, 2.0])


def test_risque_volatilite_plafonnee():
    r = simuler_risque([0.0, 0.0, 0.0, 0.0, 0.0, 1000.0])
    assert r["volatilite_pct"] <= 100
