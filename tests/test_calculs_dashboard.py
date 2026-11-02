import numpy as np
from app.calculs_dashboard import (cumul, etiquettes_mois, moyenne_mobile, parts, pic_creux,
                                   tendance_pct_par_mois, variation_mensuelle)


def test_etiquettes_mois_annee_au_debut_et_en_janvier():
    p = [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]
    assert etiquettes_mois(p) == ["Nov 25", "Déc", "Jan 26", "Fév"]


def test_moyenne_mobile():
    m = moyenne_mobile([10, 20, 30, 40], 3)
    assert np.isnan(m[0]) and np.isnan(m[1]) and m[2] == 20 and m[3] == 30


def test_variation_mensuelle_et_division_par_zero():
    v = variation_mensuelle([100, 150, 0, 50])
    assert round(v[0], 6) == 50.0 and round(v[1], 6) == -100.0 and np.isnan(v[2])
    assert len(variation_mensuelle([5])) == 0


def test_cumul_et_pic_creux():
    assert cumul([1, 2, 3]).tolist() == [1, 3, 6]
    assert pic_creux([5, 9, 1, 4]) == (1, 2)
    assert pic_creux([1, 2]) == (None, None)


def test_parts_regroupe_le_reste():
    res = parts({"a": 50, "b": 30, "c": 10, "d": 6, "e": 4}, top=3)
    assert [r[0] for r in res] == ["a", "b", "c", "Autres"]
    assert round(sum(r[2] for r in res), 6) == 100.0
    assert parts({"a": 0}) == []


def test_tendance():
    assert round(tendance_pct_par_mois([100, 110, 120, 130]), 2) > 0
    assert tendance_pct_par_mois([1, 2]) is None
