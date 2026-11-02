import pandas as pd
import pytest
from etl.normalisation import normaliser, deviner_mapping


def _df():
    return pd.DataFrame({
        "Date": ["03/02/2026", "04/02/2026", "04/02/2026"],
        "Article": ["riz 50kg", "huile 5l", "huile 5l"],
        "Qté": [2, 1, 1], "PU": ["85 000", "42 000", "42 000"],
        "Nom client": ["rakoto jean", "rabe", "rabe"], "Vendeur": ["Aina", None, None]})


def test_detection_et_normalisation():
    m = deviner_mapping(_df().columns)
    v, r = normaliser(_df(), m, "Toliara")
    assert r["lignes_valides"] == 2 and r["doublons_supprimes"] == 1
    assert v.loc[0, "montant"] == 170000
    assert v["agence"].unique().tolist() == ["Toliara"]


def test_unite_kAr():
    df = pd.DataFrame({"d": ["01/01/2026"], "p": ["x"], "q": [2], "m": ["145,0"], "c": ["a"]})
    v, _ = normaliser(df, dict(date="d", produit="p", quantite="q", montant="m", client="c"),
                      "Test", multiplicateur=1000)
    assert v.loc[0, "montant"] == 145000


def test_colonne_obligatoire_manquante():
    with pytest.raises(ValueError):
        normaliser(_df(), {"date": "Date"}, "X")
