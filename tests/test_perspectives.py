import numpy as np
import pandas as pd
from ml.anomalies import analyser, appliquer_regles, classer
from ml.backtest import backtest_glissant, diagnostic
from ml.segmentation import segmenter_depuis
from ml.series import serie_agence


def _ventes(n=300, graine=0):
    r = np.random.default_rng(graine)
    prix = {"A": 100000.0, "B": 500000.0, "C": 2000000.0}
    lignes = []
    for i in range(n):
        p = r.choice(list(prix))
        q = int(r.integers(1, 5))
        lignes.append(dict(id_vente=i, agence=r.choice(["X", "Y"]), produit=p, quantite=q,
                           prix_unitaire=prix[p], montant=q * prix[p], client=f"c{i % 40}", date="2026-03-01"))
    return pd.DataFrame(lignes)


def test_regle_prix_aberrant_et_niveau_eleve():
    df = _ventes()
    df.loc[5, ["prix_unitaire", "montant"]] = [df.loc[5, "prix_unitaire"] * 3, df.loc[5, "quantite"] * df.loc[5, "prix_unitaire"] * 3]
    r = appliquer_regles(df)
    assert any("Prix unitaire" in m for m in r.loc[5, "regles"])
    assert r.loc[5, "justifiee"] is False or not r.loc[5, "justifiee"]


def test_incoherence_montant_detectee():
    df = _ventes()
    df.loc[7, "montant"] = df.loc[7, "montant"] * 1.5
    r = appliquer_regles(df)
    assert any("Montant différent" in m for m in r.loc[7, "regles"])


def test_client_anonyme_gros_montant():
    df = _ventes()
    idx = df["montant"].idxmax()
    df.loc[idx, "client"] = "Client Anonyme"
    r = appliquer_regles(df)
    assert any("anonyme" in m.lower() for m in r.loc[idx, "regles"])


def test_classement_des_niveaux():
    d = pd.DataFrame({"anomalie_stat": [True, True, False, False, True],
                      "regles": [["r1"], [], ["r1"], [], []],
                      "justifiee": [False, True, False, False, False]})
    n = classer(d)["niveau"].tolist()
    assert n[:3] == ["Élevé", "Faible", "Moyen"] and pd.isna(n[3]) and n[4] == "Moyen"


def test_analyser_gros_montant_conforme_est_relativise():
    r = analyser(_ventes())
    assert len(r) > 0 and "Élevé" not in set(r["niveau"])     # aucune règle aggravante dans des données cohérentes
    assert set(r["niveau"]) <= {"Faible", "Moyen"}


def test_backtest_et_diagnostic():
    y = [100, 105, 110, 115, 120, 125, 130, 135, 140.0]        # tendance linéaire parfaite
    bt = backtest_glissant(y)
    assert len(bt) == 5
    d = diagnostic(y)
    assert d["meilleur_global"] == "Régression linéaire"
    assert d["tableau"].iloc[0]["mae"] < 1e-6
    assert d["retenu"] is not None and d["recommandation"]


def test_backtest_historique_trop_court():
    assert backtest_glissant([1, 2, 3, 4]).empty
    assert diagnostic([1, 2, 3, 4])["retenu"] is None


def test_serie_agence_ignore_les_mois_avant_ouverture():
    piv = pd.DataFrame({"Ancienne": [10, 20, 30, 40], "Recente": [0, 0, 5, 6]}, index=["2026-01", "2026-02", "2026-03", "2026-04"])
    assert serie_agence(piv, "Recente") == (["2026-03", "2026-04"], [5.0, 6.0])


def test_segmentation_enrichie():
    r = np.random.default_rng(3)
    n = 30
    ag = pd.DataFrame({"id_agent": range(n), "agent": [f"a{i}" for i in range(n)], "agence": r.choice(["X", "Y"], n),
                       "ca": r.random(n) * 1e8, "n": r.integers(10, 60, n), "clients": r.integers(5, 40, n),
                       "produits": r.integers(3, 10, n), "objectif": 0})
    men = pd.DataFrame([dict(id_agent=i, annee=2026, mois=m, ca=float(r.random() * 1e7)) for i in range(n) for m in range(1, 7)])
    s = segmenter_depuis(ag, men, 3)
    assert set(s["segment"]) == {"À accompagner", "Réguliers", "Performants"}
    assert {"clients", "produits", "irregularite", "etiquette"} <= set(s.columns)
    moy = s.groupby("segment")["ca"].mean()
    assert moy["Performants"] > moy["À accompagner"]
