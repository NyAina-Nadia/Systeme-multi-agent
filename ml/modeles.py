"""Modèles de prévision du CA (sans accès base de données : testables seuls)."""
import numpy as np
from sklearn.linear_model import LinearRegression

try:
    from xgboost import XGBRegressor
    XGBOOST_DISPONIBLE = True
except ImportError:
    XGBOOST_DISPONIBLE = False


MODELS = [
    "Moyenne mobile (3 mois)",
    "Régression linéaire",
    "Lissage exponentiel"
]

if XGBOOST_DISPONIBLE:
    MODELS.append("XGBoost")


def _lissage_exponentiel(y, alpha):
    l = y[0]

    for v in y[1:]:
        l = alpha * v + (1 - alpha) * l

    return l


def _predire(nom_modele, y, horizon):
    """
    Effectue une prévision selon le modèle choisi.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)

    if n == 0:
        return [0.0] * horizon

    # 1. Moyenne mobile sur les 3 dernières périodes
    if nom_modele == "Moyenne mobile (3 mois)":
        return [
            float(np.mean(y[-3:]))
        ] * horizon

    # 2. Régression linéaire
    elif nom_modele == "Régression linéaire":
        modele = LinearRegression()

        X = np.arange(n).reshape(-1, 1)
        modele.fit(X, y)

        X_futur = np.arange(
            n, n + horizon
        ).reshape(-1, 1)

        return [
            float(v)
            for v in modele.predict(X_futur)
        ]

    # 3. XGBoost
    elif nom_modele == "XGBoost":
        if not XGBOOST_DISPONIBLE:
            raise ImportError(
                "XGBoost n'est pas installé."
            )

        modele = XGBRegressor(
            n_estimators=50,
            max_depth=2,
            random_state=42,
            objective="reg:squarederror"
        )

        X = np.arange(n).reshape(-1, 1)
        modele.fit(X, y)

        X_futur = np.arange(
            n, n + horizon
        ).reshape(-1, 1)

        return [
            float(v)
            for v in modele.predict(X_futur)
        ]

    # 4. Lissage exponentiel
    elif nom_modele == "Lissage exponentiel":
        if n == 1:
            meilleur_alpha = 0.3
        else:
            alphas = [0.1, 0.3, 0.5, 0.7]

            meilleur_alpha = min(
                alphas,
                key=lambda a: sum(
                    abs(
                        y[i]
                        - _lissage_exponentiel(y[:i], a)
                    )
                    for i in range(1, n)
                )
            )

        valeur = _lissage_exponentiel(
            y, meilleur_alpha
        )

        return [float(valeur)] * horizon

    else:
        raise ValueError(
            f"Modèle de prévision inconnu : {nom_modele}"
        )
