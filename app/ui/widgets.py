"""Composants visuels réutilisables (cartes, KPI, bandeau, badges, notifications)."""
import datetime as dt
import pyqtgraph as pg
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtCore import Qt, QTimer
from app.theme import P

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS  = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


def date_longue(d: dt.date | None = None) -> str:
    d = d or dt.date.today()
    return f"{JOURS[d.weekday()].capitalize()} {d.day} {MOIS[d.month - 1]} {d.year}"


def ombre(widget, flou=20, decalage=3):
    e = QGraphicsDropShadowEffect(widget)
    e.setBlurRadius(flou)
    e.setOffset(0, decalage)
    e.setColor(QColor(14, 40, 42, 45 if P["mode"] == "sombre" else 22))
    widget.setGraphicsEffect(e)


def repolir(w):
    w.style().unpolish(w); w.style().polish(w)
    return w


class Carte(QFrame):
    """Conteneur arrondi avec ombre douce."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("carte")
        ombre(self)


def badge(texte, type_="gris"):
    """Pastille colorée : type_ = vert | rouge | ambre | gris."""
    lbl = QLabel(texte)
    lbl.setProperty("badge", type_)
    lbl.setAlignment(Qt.AlignCenter)
    return repolir(lbl)


class CarteKPI(Carte):
    """Indicateur : icône, libellé, valeur, sous-texte et mini-courbe optionnelle."""
    def __init__(self, libelle, valeur, sous_texte="", couleur="#0E4749", icone="", delta=None,
                 serie=None, delta_inverse=False):
        super().__init__()
        self.setStyleSheet(f"QFrame#carte {{ border-top: 4px solid {couleur}; }}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 12)
        lay.setSpacing(2)

        # Ligne haute : libellé + icône
        haut = QHBoxLayout()
        lbl = QLabel(libelle.upper()); lbl.setObjectName("kpiLibelle")
        haut.addWidget(lbl, 1)
        if icone:
            ic = QLabel(icone); ic.setObjectName("kpiIcone"); haut.addWidget(ic)
        lay.addLayout(haut)

        # Valeur (taille adaptative si le texte est long)
        val = QLabel(valeur); val.setObjectName("kpiValeur")
        fm = QFontMetrics(QFont("Segoe UI", 24, QFont.Bold))
        if fm.horizontalAdvance(valeur) > 200:
            val.setStyleSheet("font-size: 18px;")
        lay.addWidget(val)

        # Ligne basse : badge delta + sous-texte
        ligne = QHBoxLayout()
        if delta is not None:
            bon = (delta >= 0) != delta_inverse
            fleche = "▲" if delta >= 0 else "▼"
            ligne.addWidget(badge(f"{fleche} {abs(delta):.1f} %", "vert" if bon else "rouge"))
            ligne.addSpacing(6)
        if sous_texte:
            sub = QLabel(sous_texte); sub.setObjectName("kpiSous")
            sub.setWordWrap(True)
            ligne.addWidget(sub, 1)
        else:
            ligne.addStretch()
        lay.addLayout(ligne)

        # Mini-courbe
        if serie and len(serie) >= 2:
            sp = pg.PlotWidget()
            sp.setFixedHeight(42)
            sp.setBackground(P["carte"])
            sp.hideAxis("left"); sp.hideAxis("bottom")
            sp.setMouseEnabled(False, False); sp.setMenuEnabled(False)
            sp.getPlotItem().setContentsMargins(0, 0, 0, 0)
            c = QColor(couleur); c.setAlpha(55)
            sp.plot(list(range(len(serie))), list(serie),
                    pen=pg.mkPen(couleur, width=2.5), fillLevel=min(serie), brush=c)
            lay.addWidget(sp)


class BandeauAccueil(QFrame):
    """Bannière dégradée en haut du tableau de bord, avec date et rôle."""
    def __init__(self, titre, sous_titre, date_texte="", role=""):
        super().__init__()
        self.setObjectName("bandeau")
        ombre(self, 28, 6)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(26, 20, 26, 20)

        # Colonne gauche : titre + sous-titre
        gauche = QVBoxLayout(); gauche.setSpacing(3)
        t = QLabel(titre); t.setObjectName("bandeauTitre")
        gauche.addWidget(t)
        self.lbl_sous = QLabel(sous_titre); self.lbl_sous.setObjectName("bandeauSous")
        gauche.addWidget(self.lbl_sous)
        lay.addLayout(gauche, 1)

        # Colonne droite : date + badge rôle
        if date_texte or role:
            droite = QVBoxLayout(); droite.setSpacing(6); droite.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if date_texte:
                d = QLabel(date_texte); d.setObjectName("bandeauDate"); d.setAlignment(Qt.AlignRight)
                droite.addWidget(d)
            if role:
                r = QLabel(role.capitalize()); r.setObjectName("bandeauRole"); r.setAlignment(Qt.AlignRight)
                droite.addWidget(r)
            lay.addLayout(droite)


class TitrePage(QWidget):
    def __init__(self, titre, sous_titre=""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 6); lay.setSpacing(0)
        t = QLabel(titre); t.setObjectName("titrePage")
        lay.addWidget(t)
        if sous_titre:
            s = QLabel(sous_titre); s.setObjectName("sousTitre")
            lay.addWidget(s)


def etiquette(texte, nom="section"):
    lbl = QLabel(texte)
    lbl.setObjectName(nom)
    lbl.setWordWrap(True)
    return lbl


def alerte(texte, type_="neutre"):
    """Bande d'alerte colorée. type_ : neutre | risque | positif | ambre."""
    noms = {"neutre": "alerteNeutre", "risque": "alerteRisque",
            "positif": "alertePositif", "ambre": "alerteAmbre"}
    icones = {"neutre": "ℹ️", "risque": "⚠️", "positif": "✅", "ambre": "🔔"}
    lbl = QLabel(f"{icones.get(type_, '')}  {texte}")
    lbl.setObjectName(noms.get(type_, "alerteNeutre"))
    lbl.setWordWrap(True)
    return lbl


def separateur_h():
    """Ligne horizontale de séparation légère."""
    sep = QFrame(); sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("background: transparent; border: none; border-top: 1px solid " + P["bordure"] + ";")
    sep.setFixedHeight(1)
    return sep


def bouton_secondaire(bouton):
    bouton.setProperty("secondaire", True)
    return repolir(bouton)


def bouton_danger(bouton):
    bouton.setProperty("danger", True)
    return repolir(bouton)


def preparer_table(table: QTableWidget):
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(40)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setShowGrid(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    return table


def item(texte, aligne_droite=False):
    it = QTableWidgetItem(str(texte))
    if aligne_droite:
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return it


def fmt_ar(valeur, millions=True):
    if millions:
        return f"{valeur/1e6:,.0f} M Ar".replace(",", " ")
    return f"{valeur:,.0f} Ar".replace(",", " ")


def afficher_toast(widget, texte, type_="info", duree=3200):
    """Notification éphémère en haut à droite de la fenêtre (type_ : info | succes | erreur)."""
    fenetre = widget.window()
    toast = QLabel(texte, fenetre)
    toast.setObjectName("toast")
    toast.setProperty("type", type_)
    repolir(toast)
    toast.setWordWrap(True)
    toast.setMaximumWidth(380)
    toast.adjustSize()
    toast.move(fenetre.width() - toast.width() - 28, 22)
    ombre(toast, 22, 4)
    toast.show(); toast.raise_()
    QTimer.singleShot(duree, toast.deleteLater)
    return toast
