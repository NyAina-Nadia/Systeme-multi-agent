import numpy as np
import pandas as pd
from ml.abc_rfm import classer_abc, calculer_rfm
from ml.scenarios import projeter
from ml.recommandations import construire_recommandations


def test_abc_classes_et_cumul():
    df = pd.DataFrame({"produit": list("abcdefghij"), "ca": [50, 20, 10, 6, 5, 3, 2, 2, 1, 1]})
    r = classer_abc(df)
    assert r["part"].sum() == 1 or abs(r["part"].sum() - 1) < 1e-9
    assert r.loc[0, "classe"] == "A" and r.iloc[-1]["classe"] == "C"
    assert set(r["classe"]) == {"A", "B", "C"}


def test_rfm_segments_ordonnes():
    rng = np.random.default_rng(1)
    n = 60
    df = pd.DataFrame({"client": [f"c{i}" for i in range(n)],
                       "derniere": pd.Timestamp("2026-09-30") - pd.to_timedelta(rng.integers(0, 250, n), unit="D"),
                       "frequence": rng.integers(1, 15, n), "montant": rng.random(n) * 1e6})
    r = calculer_rfm(df, 3)
    assert set(r["segment"]) <= {"Clients fidèles", "Clients réguliers", "Clients à relancer"}
    moy = r.groupby("segment")["montant"].mean()
    assert moy.get("Clients fidèles", 1) >= moy.get("Clients à relancer", 0) * 0.5


def test_rfm_sans_frequence():
    rng = np.random.default_rng(2)
    n = 40
    df = pd.DataFrame({"client": [f"c{i}" for i in range(n)], "frequence": 1,
                       "derniere": pd.Timestamp("2026-09-30") - pd.to_timedelta(rng.integers(0, 250, n), unit="D"),
                       "montant": rng.random(n) * 1e6})
    r = calculer_rfm(df, 3)
    assert r.attrs["frequence_exploitable"] is False
    assert "Clients fidèles" not in set(r["segment"])
    assert set(r["segment"]) <= {"Petits acheteurs", "Acheteurs moyens", "Gros acheteurs"}


def test_scenario_neutre_et_hausse():
    y = [100, 100, 100, 100, 100, 100]
    base = projeter(y, objectif=900, mois_a_projeter=3)
    assert base["cumul_actuel"] == 600 and base["cumul_base"] == 900
    assert base["gain_scenario"] == 0
    plus = projeter(y, 900, variation_volume=10, variation_prix=10, mois_a_projeter=3)
    assert abs(plus["mensuel_scenario"] - 121) < 1e-9
    assert plus["cumul_scenario"] > base["cumul_base"]
    assert abs(base["hausse_requise_pct"]) < 1e-9


def test_recommandations_regles():
    pivot = pd.DataFrame({"A": [100, 100, 100, 70, 70, 70], "B": [50] * 6})
    kpi = pd.DataFrame({"agence": ["A", "B"], "objectif": [1000, 100], "ca": [510, 300]})
    produits = pd.DataFrame({"agence": ["A", "A", "B"], "produit": ["x", "y", "z"], "ca": [90, 10, 100]})
    clients = pd.DataFrame({"agence": ["A"] * 6, "client": list("abcdef"), "frequence": [3, 4, 5, 2, 6, 1],
                            "derniere": pd.to_datetime(["2026-09-30", "2026-05-01", "2026-04-01", "2026-03-01",
                                                        "2026-02-01", "2026-01-01"])})
    agents = pd.DataFrame({"agence": ["A"] * 3, "agent": ["u", "v", "w"], "objectif": [0, 0, 0], "ca": [300, 200, 10]})
    reco = construire_recommandations(pivot, kpi, produits, clients, agents)
    themes = {(r["agence"], r["theme"]) for r in reco}
    assert ("A", "Tendance") in themes and ("A", "Objectif") in themes
    assert ("A", "Produits") in themes and ("A", "Clients") in themes and ("A", "Agents") in themes
    assert ("B", "Produits") in themes     # 100 % sur un seul produit
    assert reco[0]["priorite"] == "Haute"  # tri par priorité
