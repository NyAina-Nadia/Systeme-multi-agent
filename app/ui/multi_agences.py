"""Classement multi-agences : CA réalisé vs objectif, barre de progression, écart coloré."""
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QFrame,
                               QLabel, QProgressBar, QHeaderView, QScrollArea, QSizePolicy)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from app.db import engine
from app.theme import P, SUCCES, ACCENT, OR
from app.ui.widgets import TitrePage, Carte, etiquette, CarteKPI, preparer_table, item

REQUETE = """
    SELECT da.agence, da.objectif,
        COALESCE(SUM(f.montant), 0) AS ca_realise
    FROM dim_agence da
    LEFT JOIN fait_vente f ON f.id_agence = da.id_agence
    GROUP BY da.agence, da.objectif
    ORDER BY ca_realise DESC
"""

# Seuils visuels (en % d'atteinte de l'objectif)
SEUIL_OK   = 100   # ≥ 100 % → vert
SEUIL_WARN =  75   # ≥  75 % → ambre
                   # <  75 % → rouge


def _couleur_atteinte(pct: float) -> tuple[str, str]:
    """Retourne (couleur_fond, couleur_texte) selon le seuil, adaptées au thème courant."""
    if pct >= SEUIL_OK:
        return P["positif_bg"], P["positif_txt"]
    if pct >= SEUIL_WARN:
        return P["ambre_bg"], P["ambre_txt"]
    return P["risque_bg"], P["risque_txt"]


def _fmt(valeur_ar: float) -> str:
    return f"{valeur_ar / 1e6:,.0f} M Ar".replace(",", " ")


class BarreObjectif(QWidget):
    """Mini-barre de progression avec pourcentage intégré, couleur adaptée au thème."""
    def __init__(self, pct: float, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(8)

        barre = QProgressBar()
        barre.setRange(0, 100)
        barre.setValue(min(int(pct), 100))
        barre.setTextVisible(False)
        barre.setFixedHeight(10)
        barre.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if pct >= SEUIL_OK:
            chunk_color = SUCCES
        elif pct >= SEUIL_WARN:
            chunk_color = OR
        else:
            chunk_color = ACCENT

        barre.setStyleSheet(
            f"QProgressBar {{ background: {P['bordure']}; border: none; border-radius: 5px; }}"
            f"QProgressBar::chunk {{ background: {chunk_color}; border-radius: 5px; }}"
        )

        lbl = QLabel(f"{pct:.0f} %")
        lbl.setFixedWidth(46)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f = QFont(); f.setPointSize(10); f.setBold(True)
        lbl.setFont(f)
        lbl.setStyleSheet(f"color: {chunk_color}; background: transparent;")

        lay.addWidget(barre, 1)
        lay.addWidget(lbl)


class MultiAgencesScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()

        defil = QScrollArea()
        defil.setWidgetResizable(True)
        defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        page_lay = QVBoxLayout(contenu)
        page_lay.setContentsMargins(0, 0, 10, 0)
        page_lay.setSpacing(16)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self)
        ext.setContentsMargins(0, 0, 0, 0)
        ext.addWidget(defil)

        page_lay.addWidget(TitrePage(
            "Multi-agences",
            "Classement des agences — CA réalisé vs objectif"
        ))

        self.zone_kpi = QHBoxLayout()
        self.zone_kpi.setSpacing(16)
        page_lay.addLayout(self.zone_kpi)

        carte = Carte()
        carte_lay = QVBoxLayout(carte)
        carte_lay.setContentsMargins(18, 14, 18, 18)
        carte_lay.setSpacing(10)
        carte_lay.addWidget(etiquette("Détail par agence"))

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "#", "Agence", "CA réalisé", "Objectif", "Atteinte"
        ])
        preparer_table(self.table)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 140)
        self.table.verticalHeader().setDefaultSectionSize(46)

        carte_lay.addWidget(self.table)
        page_lay.addWidget(carte)

        self.rafraichir()

    def _vider_kpi(self):
        while self.zone_kpi.count():
            it = self.zone_kpi.takeAt(0)
            if it.widget():
                it.widget().setParent(None)

    def rafraichir(self):
        df = pd.read_sql(REQUETE, engine)
        self._vider_kpi()
        self.table.setRowCount(0)

        if df.empty:
            return

        total_ca  = df["ca_realise"].sum()
        total_obj = df["objectif"].fillna(0).sum()
        atteinte_globale = total_ca / total_obj * 100 if total_obj else 0
        nb_ok     = int((df["ca_realise"] >= df["objectif"].fillna(0)).sum())
        meilleure = df.iloc[0]["agence"] if len(df) else "—"

        self.zone_kpi.addWidget(CarteKPI(
            "CA total réalisé", _fmt(total_ca),
            f"objectif global : {_fmt(total_obj)}", P["serie1"], "📊"
        ))
        self.zone_kpi.addWidget(CarteKPI(
            "Atteinte globale", f"{atteinte_globale:.0f} %",
            "CA réalisé ÷ objectif total",
            SUCCES if atteinte_globale >= 100 else (OR if atteinte_globale >= 75 else ACCENT),
            "🎯"
        ))
        self.zone_kpi.addWidget(CarteKPI(
            "Agences à l'objectif", f"{nb_ok} / {len(df)}",
            "ont atteint ou dépassé leur objectif", SUCCES, "✅"
        ))
        self.zone_kpi.addWidget(CarteKPI(
            "1re agence", meilleure,
            "CA réalisé le plus élevé", P["serie2"], "🏆"
        ))

        self.table.setRowCount(len(df))

        for rang, (_, row) in enumerate(df.iterrows()):
            ca  = float(row["ca_realise"])
            obj = float(row["objectif"]) if row["objectif"] else 0.0
            pct = ca / obj * 100 if obj > 0 else 0.0
            fond, _ = _couleur_atteinte(pct)

            medailles = {0: "🥇", 1: "🥈", 2: "🥉"}
            it_rang = _item_centre(medailles.get(rang, str(rang + 1)))
            self.table.setItem(rang, 0, it_rang)

            it_agence = _item_centre(str(row["agence"]))
            if rang == 0:
                f = QFont(); f.setBold(True)
                it_agence.setFont(f)
            self.table.setItem(rang, 1, it_agence)

            self.table.setItem(rang, 2, _item_droite(_fmt(ca)))

            it_obj = _item_droite(_fmt(obj) if obj > 0 else "—")
            if obj == 0:
                it_obj.setForeground(QColor(P["doux"]))
            self.table.setItem(rang, 3, it_obj)

            self.table.setCellWidget(rang, 4, BarreObjectif(pct))

            q_fond = QColor(fond)
            q_fond.setAlpha(80)
            for col in range(4):
                it = self.table.item(rang, col)
                if it:
                    it.setBackground(q_fond)
                    it.setForeground(QColor(P["texte"]))


def _item_centre(texte: str):
    from PySide6.QtWidgets import QTableWidgetItem
    it = QTableWidgetItem(str(texte))
    it.setTextAlignment(Qt.AlignCenter)
    return it


def _item_droite(texte: str):
    from PySide6.QtWidgets import QTableWidgetItem
    it = QTableWidgetItem(str(texte))
    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return it