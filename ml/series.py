"""Séries mensuelles par agence (sans dépendance à la base : testable seul)."""

MOIS_MINIMUM = 6   # 3 mois pour apprendre + 3 mois pour tester les modèles


def serie_agence(piv, agence):
    """(périodes, valeurs) d'une agence, SANS les mois qui précèdent sa première vente.
    Une agence ouverte en avril n'a pas « 0 Ar de CA » en janvier : elle n'existait pas encore."""
    if piv is None or len(piv) == 0 or agence not in piv.columns:
        return [], []
    periodes, valeurs = piv.index.tolist(), [float(v) for v in piv[agence].tolist()]
    debut = next((i for i, v in enumerate(valeurs) if v > 0), len(valeurs))
    return periodes[debut:], valeurs[debut:]
