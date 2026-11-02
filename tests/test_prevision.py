from ml.prevision import prevoir, historique_mensuel_par_agence

def test_historique_non_vide():
    piv = historique_mensuel_par_agence()
    assert len(piv) > 0, "L'historique mensuel ne doit pas être vide"

def test_prevoir_retourne_trois_mois():
    piv = historique_mensuel_par_agence()
    if piv.empty:
        return
    premiere_agence = piv.columns[0]
    resultat = prevoir(premiere_agence)
    assert resultat is not None
    assert len(resultat["prevision"]) == 3
    assert resultat["modele_retenu"] in [
        "Moyenne mobile (3 mois)", "Régression linéaire", "Lissage exponentiel"
    ]