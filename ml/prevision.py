import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from app.db import engine

from ml.modeles import MODELS, XGBOOST_DISPONIBLE, _predire, _lissage_exponentiel   # noqa: F401
from ml.series import MOIS_MINIMUM, serie_agence


def historique_mensuel_par_agence() -> pd.DataFrame:
    """
    Retourne un tableau pivoté :
    une colonne par agence, une ligne par mois.
    """

    requete = """
    SELECT
        dd.annee,
        dd.mois,
        da.agence,
        SUM(f.montant) AS ca
    FROM fait_vente f
    JOIN dim_date dd
        ON dd.id_temps = f.id_temps
    JOIN dim_agence da
        ON da.id_agence = f.id_agence
    GROUP BY
        dd.annee,
        dd.mois,
        da.agence
    ORDER BY
        dd.annee,
        dd.mois
    """

    df = pd.read_sql(requete, engine)

    if df.empty:
        return pd.DataFrame()

    df["periode"] = (
        df["annee"].astype(str)
        + "-"
        + df["mois"].astype(str).str.zfill(2)
    )

    piv = df.pivot_table(
        index="periode",
        columns="agence",
        values="ca",
        aggfunc="sum"
    ).fillna(0) / 1e6

    # Garantir l'ordre chronologique des périodes
    piv = piv.sort_index()

    return piv


def prevoir(agence: str, horizon: int = 3) -> dict:
    """
    Compare les modèles sur les 3 derniers mois disponibles,
    retient celui qui présente la plus petite MAE,
    puis prévoit les 3 prochains mois par défaut.
    """

    piv = historique_mensuel_par_agence()

    if piv.empty or agence not in piv.columns:
        return None

    periodes, y = serie_agence(piv, agence)   # sans les mois précédant la première vente

    if len(y) < MOIS_MINIMUM:
        return None

    # Séparation des données d'entraînement et de test
    y_train = y[:-3]
    y_test = y[-3:]

    erreurs = {}
    mapes = {}

    # Évaluation des modèles
    for nom in MODELS:
        try:
            pred_test = _predire(
                nom,
                y_train,
                len(y_test)
            )

            erreurs[nom] = float(
                mean_absolute_error(
                    y_test,
                    pred_test
                )
            )
            reel = np.array(y_test, dtype=float)
            reel[reel == 0] = np.nan
            mapes[nom] = float(
                np.nanmean(np.abs((reel - np.array(pred_test)) / reel)) * 100
            )

        except Exception as e:
            print(
                f"Erreur pour le modèle {nom} : {e}"
            )

    if not erreurs:
        raise RuntimeError(
            "Aucun modèle de prévision n'a pu être évalué."
        )

    # Sélection du modèle avec la MAE la plus faible
    meilleur = min(
        erreurs,
        key=erreurs.get
    )

    # Calcul des résidus sur la période de test
    pred_test_meilleur = _predire(
        meilleur,
        y_train,
        len(y_test)
    )

    residus = (
        np.array(y_test)
        - np.array(pred_test_meilleur)
    )

    ecart_type = float(
        np.std(residus)
    ) or 1.0

    # Prévision future avec toutes les données disponibles
    prevision = _predire(
        meilleur,
        y,
        horizon
    )

    # Construction des périodes futures
    derniere_periode = pd.Period(
        periodes[-1],
        freq="M"
    )

    periodes_futures = [
        str(derniere_periode + i)
        for i in range(1, horizon + 1)
    ]

    return {
        "agence": agence,
        "historique": y,
        "periodes_historique": list(periodes),
        "periodes_prevision": periodes_futures,
        "prevision": prevision,
        "borne_basse": [
            max(0, v - 1.28 * ecart_type)
            for v in prevision
        ],
        "borne_haute": [
            v + 1.28 * ecart_type
            for v in prevision
        ],
        "modele_retenu": meilleur,
        "erreurs_mae": erreurs,
        "erreurs_mape": mapes,
    }