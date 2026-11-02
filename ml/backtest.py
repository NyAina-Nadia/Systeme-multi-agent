"""
Évaluation régulière des prévisions : backtest glissant (« rolling origin »).

Principe : pour chaque mois t à partir de `min_apprentissage`, chaque modèle apprend sur les mois
précédents (y[:t]) et prévoit le mois t ; on compare à la valeur réelle. On obtient ainsi l'évolution
de l'erreur de chaque modèle au fil du temps, et non une seule mesure sur 3 mois.
Ce module ne dépend pas de la base : il est testable seul.
"""
import numpy as np
import pandas as pd
from ml.modeles import MODELS, _predire


def backtest_glissant(y, modeles=None, min_apprentissage=4) -> pd.DataFrame:
    """Retourne un DataFrame (une ligne par mois testé) : t, reel, <modèle>_prev, <modèle>_err (erreur absolue)."""
    y = [float(v) for v in y]
    modeles = list(modeles or MODELS)
    lignes = []
    for t in range(min_apprentissage, len(y)):
        ligne = {"t": t, "reel": y[t]}
        for nom in modeles:
            try:
                p = _predire(nom, y[:t], 1)[0]
            except Exception:
                p = float("nan")
            ligne[f"{nom}_prev"] = p
            ligne[f"{nom}_err"] = abs(y[t] - p) if np.isfinite(p) else float("nan")
        lignes.append(ligne)
    return pd.DataFrame(lignes)


def modele_retenu_application(y, modeles=None) -> str:
    """Règle de l'application : le modèle le plus précis sur les 3 derniers mois (appris sur le reste)."""
    y = [float(v) for v in y]
    modeles = list(modeles or MODELS)
    erreurs = {}
    for nom in modeles:
        try:
            pred = _predire(nom, y[:-3], 3)
            erreurs[nom] = float(np.mean(np.abs(np.array(y[-3:]) - np.array(pred))))
        except Exception:
            continue
    return min(erreurs, key=erreurs.get) if erreurs else modeles[0]


def synthese_backtest(bt: pd.DataFrame, modeles=None, derniers=3, seuil_derive=1.5) -> dict:
    """Résume le backtest : erreurs par modèle, meilleur global vs récent, dérive de l'erreur."""
    modeles = list(modeles or MODELS)
    if bt.empty:
        return {"tableau": pd.DataFrame(), "meilleur_global": None, "meilleur_recent": None, "n_tests": 0}
    lignes = []
    for nom in modeles:
        err = bt[f"{nom}_err"]
        prev = bt[f"{nom}_prev"]
        reel = bt["reel"].replace(0, np.nan)
        lignes.append({
            "modele": nom,
            "mae": float(err.mean()),
            "mape": float((err / reel).mean() * 100),
            "mae_recent": float(err.tail(derniers).mean()),
            "biais": float((prev - bt["reel"]).mean()),
        })
    tab = pd.DataFrame(lignes).sort_values("mae").reset_index(drop=True)
    return {
        "tableau": tab,
        "meilleur_global": tab.sort_values("mae").iloc[0]["modele"],
        "meilleur_recent": tab.sort_values("mae_recent").iloc[0]["modele"],
        "n_tests": len(bt),
        "seuil_derive": seuil_derive,
    }


def diagnostic(y, modeles=None, min_apprentissage=4, derniers=3, seuil_derive=1.5) -> dict:
    """Diagnostic complet pour une série : backtest + synthèse + modèle retenu + dérive + recommandation."""
    modeles = list(modeles or MODELS)
    bt = backtest_glissant(y, modeles, min_apprentissage)
    s = synthese_backtest(bt, modeles, derniers, seuil_derive)
    if bt.empty:
        return {**s, "backtest": bt, "retenu": None, "derive": None, "recommandation": "Historique insuffisant."}
    retenu = modele_retenu_application(y, modeles)
    err = bt[f"{retenu}_err"]
    avant = err.iloc[:-derniers] if len(err) > derniers else err.iloc[:0]
    derive = None
    if len(avant) >= 1 and avant.mean() > 0:
        derive = float(err.tail(derniers).mean() / avant.mean())     # >1 : l'erreur récente dépasse l'erreur passée
    msgs = []
    if retenu != s["meilleur_global"]:
        msgs.append(f"Le modèle retenu ({retenu}) n'est pas le plus précis sur l'ensemble de l'historique "
                    f"({s['meilleur_global']}) : à surveiller.")
    else:
        msgs.append(f"Le modèle retenu ({retenu}) est aussi le plus précis sur l'ensemble de l'historique.")
    if derive is not None and derive >= seuil_derive:
        msgs.append(f"L'erreur récente est {derive:.1f} fois l'erreur passée : le modèle se dégrade, "
                    f"une réévaluation avec de nouvelles données est conseillée.")
    elif derive is not None:
        msgs.append("L'erreur récente reste du même ordre que l'erreur passée : pas de dérive détectée.")
    return {**s, "backtest": bt, "retenu": retenu, "derive": derive, "recommandation": " ".join(msgs)}
