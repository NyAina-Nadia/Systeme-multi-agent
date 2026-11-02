"""Calculs des graphiques du tableau de bord (sans Qt ni base de données : testables seuls)."""
import numpy as np

MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]


def etiquettes_mois(periodes):
    """[(2026, 1), (2026, 2), ...] -> ['Jan 26', 'Fév', ...] : l'année n'apparaît qu'au début et en janvier."""
    sortie = []
    for i, (annee, mois) in enumerate(periodes):
        mois = int(mois)
        sortie.append(f"{MOIS[mois - 1]} {str(int(annee))[2:]}" if (i == 0 or mois == 1) else MOIS[mois - 1])
    return sortie


def moyenne_mobile(y, n=3):
    """Moyenne mobile sur n mois ; les n-1 premières valeurs sont NaN (fenêtre incomplète)."""
    y = np.asarray(y, dtype=float)
    out = np.full(len(y), np.nan)
    for i in range(n - 1, len(y)):
        out[i] = y[i - n + 1:i + 1].mean()
    return out


def variation_mensuelle(y):
    """Variation en % d'un mois sur l'autre (longueur len(y)-1). NaN si le mois précédent vaut 0."""
    y = np.asarray(y, dtype=float)
    if len(y) < 2:
        return np.array([])
    prec = y[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(prec != 0, (y[1:] / prec - 1) * 100, np.nan)
    return v


def cumul(y):
    return np.cumsum(np.asarray(y, dtype=float))


def pic_creux(y):
    """(indice du mois le plus fort, indice du mois le plus faible) ; None si moins de 3 mois."""
    y = np.asarray(y, dtype=float)
    if len(y) < 3:
        return None, None
    return int(np.argmax(y)), int(np.argmin(y))


def parts(valeurs: dict, top=8):
    """{nom: valeur} -> [(nom, valeur, part en %)] trié par valeur décroissante ; le reste est regroupé en « Autres »."""
    total = float(sum(valeurs.values()))
    if total <= 0:
        return []
    tri = sorted(valeurs.items(), key=lambda kv: kv[1], reverse=True)
    garde, reste = tri[:top], tri[top:]
    res = [(n, float(v), v / total * 100) for n, v in garde]
    if reste:
        v = float(sum(x for _, x in reste))
        res.append(("Autres", v, v / total * 100))
    return res


def tendance_pct_par_mois(y):
    """Pente de la droite de régression, en % de la moyenne par mois (None si < 3 mois)."""
    y = np.asarray(y, dtype=float)
    if len(y) < 3 or y.mean() == 0:
        return None
    pente = np.polyfit(np.arange(len(y)), y, 1)[0]
    return float(pente / y.mean() * 100)
