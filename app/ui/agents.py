"""Agents & objectifs : réalisé par agent, barre de progression colorée, formulaire d'objectif."""
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
                               QTableWidget, QProgressBar, QLineEdit, QPushButton,
                               QMessageBox, QScrollArea, QFrame, QSizePolicy, QHeaderView)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from app.db import engine
from app.audit import journaliser
from app.theme import P, ACCENT, OR, SUCCES
from app.ui.widgets import (TitrePage, Carte, CarteKPI, etiquette, preparer_table,
                            item, fmt_ar, bouton_secondaire, afficher_toast)

REQUETE = """
    SELECT dagt.id_agent, dagt.id_agence, dagt.agent, da.agence,
           COALESCE(dagt.objectif, 0) AS objectif,
           COALESCE(SUM(f.montant), 0) AS ca,
           COUNT(f.id_vente) AS nb_ventes
    FROM dim_agent dagt
    JOIN dim_agence da ON da.id_agence = dagt.id_agence
    LEFT JOIN fait_vente f ON f.id_agent = dagt.id_agent
    GROUP BY dagt.id_agent, dagt.id_agence, dagt.agent, da.agence, dagt.objectif
    ORDER BY ca DESC
"""

SEUIL_OK   = 100
SEUIL_WARN =  70


def _couleur(pct: float) -> str:
    """Couleur de chunk selon le taux d'atteinte."""
    if pct >= SEUIL_OK:
        return SUCCES
    if pct >= SEUIL_WARN:
        return OR
    return ACCENT


def _fond(pct: float) -> tuple[str, str]:
    """(fond, texte) de ligne selon le taux d'atteinte."""
    if pct >= SEUIL_OK:
        return P["positif_bg"], P["positif_txt"]
    if pct >= SEUIL_WARN:
        return P["ambre_bg"], P["ambre_txt"]
    return P["risque_bg"], P["risque_txt"]


class BarreAgent(QWidget):
    """Barre de progression + label %, colorée selon le seuil."""
    def __init__(self, pct: float | None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(8)

        barre = QProgressBar()
        barre.setRange(0, 150)
        barre.setTextVisible(False)
        barre.setFixedHeight(10)
        barre.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if pct is not None:
            barre.setValue(int(min(150, pct)))
            couleur = _couleur(pct)
            texte   = f"{pct:.0f} %"
        else:
            barre.setValue(0)
            couleur = P["bordure"]
            texte   = "—"

        barre.setStyleSheet(
            f"QProgressBar {{ background: {P['bordure']}; border: none; border-radius: 5px; }}"
            f"QProgressBar::chunk {{ background: {couleur}; border-radius: 5px; }}"
        )

        lbl = QLabel(texte)
        lbl.setFixedWidth(46)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f = QFont(); f.setPointSize(10); f.setBold(pct is not None)
        lbl.setFont(f)
        lbl.setStyleSheet(f"color: {couleur}; background: transparent;")

        lay.addWidget(barre, 1)
        lay.addWidget(lbl)


class AgentsScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        self.df = pd.DataFrame()

        # ── Défilement ───────────────────────────────────────────────────────
        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(16); layout.setContentsMargins(0, 0, 10, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        # ── En-tête ──────────────────────────────────────────────────────────
        entete = QHBoxLayout()
        entete.addWidget(
            TitrePage("Agents & objectifs",
                      "CA réalisé par agent et taux d'atteinte de l'objectif individuel"), 1)
        l = QLabel("Agence"); l.setObjectName("sousTitre")
        self.filtre = QComboBox(); self.filtre.setMinimumWidth(190)
        self.filtre.addItem("Toutes les agences", None)
        entete.addWidget(l); entete.addWidget(self.filtre)
        layout.addLayout(entete)

        # ── KPI ──────────────────────────────────────────────────────────────
        self.zone_kpi = QHBoxLayout(); self.zone_kpi.setSpacing(16)
        layout.addLayout(self.zone_kpi)

        # ── Tableau ──────────────────────────────────────────────────────────
        carte_table = Carte()
        lt = QVBoxLayout(carte_table); lt.setContentsMargins(18, 14, 18, 18); lt.setSpacing(10)
        lt.addWidget(etiquette("Détail par agent"))

        self.table = QTableWidget()
        preparer_table(self.table)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Agent", "Agence", "Ventes", "CA réalisé", "Objectif", "Atteinte"])
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setMinimumHeight(340)
        self.table.itemSelectionChanged.connect(self.selection_changee)

        lt.addWidget(self.table)
        layout.addWidget(carte_table)

        # ── Formulaire d'objectif ─────────────────────────────────────────────
        carte_form = Carte()
        lf = QVBoxLayout(carte_form); lf.setContentsMargins(18, 14, 18, 18); lf.setSpacing(10)
        lf.addWidget(etiquette("Définir les objectifs"))

        self.lbl_sel = QLabel("Sélectionnez un agent dans le tableau.")
        self.lbl_sel.setObjectName("sousTitre")
        lf.addWidget(self.lbl_sel)

        ligne = QHBoxLayout(); ligne.setSpacing(10)
        self.champ = QLineEdit()
        self.champ.setPlaceholderText("Objectif de l'agent en Ariary, ex. 120 000 000")
        b1 = QPushButton("💾  Enregistrer pour cet agent")
        b1.clicked.connect(self.enregistrer)
        b2 = bouton_secondaire(QPushButton("⚖️  Répartir l'objectif de l'agence équitablement"))
        b2.clicked.connect(self.repartir)
        ligne.addWidget(self.champ, 1); ligne.addWidget(b1); ligne.addWidget(b2)
        lf.addLayout(ligne)

        layout.addWidget(carte_form)

        # ── Chargement initial ────────────────────────────────────────────────
        agences = pd.read_sql("SELECT id_agence, agence FROM dim_agence ORDER BY agence", engine)
        for _, r in agences.iterrows():
            self.filtre.addItem(r["agence"], int(r["id_agence"]))
        self.filtre.currentIndexChanged.connect(self.rafraichir)
        self.rafraichir()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _vider(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().setParent(None)

    # ── Rafraîchissement ─────────────────────────────────────────────────────

    def rafraichir(self, *_):
        df = pd.read_sql(REQUETE, engine)
        for c in ("objectif", "ca"):
            df[c] = df[c].astype(float)
        a = self.filtre.currentData()
        if a:
            df = df[df["id_agence"] == a]
        self.df = df.reset_index(drop=True)

        avec  = self.df[self.df["objectif"] > 0]
        taux  = (avec["ca"] / avec["objectif"] * 100) if len(avec) else pd.Series(dtype=float)
        moy   = taux.mean() if len(taux) else None
        nb_ko = int((taux < SEUIL_WARN).sum()) if len(taux) else 0

        # KPI
        self._vider(self.zone_kpi)
        self.zone_kpi.addWidget(CarteKPI(
            "Agents", str(len(self.df)),
            "dans le périmètre affiché", P["serie1"], "👥"))
        self.zone_kpi.addWidget(CarteKPI(
            "Objectifs définis", f"{len(avec)} / {len(self.df)}",
            "agents avec objectif", OR, "🎯"))
        self.zone_kpi.addWidget(CarteKPI(
            "Atteinte moyenne", f"{moy:.0f} %" if moy is not None else "—",
            "sur les objectifs définis",
            SUCCES if (moy or 0) >= SEUIL_OK else (OR if (moy or 0) >= SEUIL_WARN else ACCENT),
            "📊"))
        self.zone_kpi.addWidget(CarteKPI(
            f"Agents sous {SEUIL_WARN} %", str(nb_ko) if len(taux) else "—",
            "à accompagner en priorité", ACCENT, "⚠️"))

        # Tableau
        self.table.setRowCount(len(self.df))
        for i, r in self.df.iterrows():
            pct = r["ca"] / r["objectif"] * 100 if r["objectif"] > 0 else None

            # Colonnes texte
            self.table.setItem(i, 0, _item(r["agent"]))
            self.table.setItem(i, 1, _item(r["agence"], centre=True))
            self.table.setItem(i, 2, _item(int(r["nb_ventes"]), droite=True))
            self.table.setItem(i, 3, _item(fmt_ar(r["ca"]), droite=True))
            self.table.setItem(i, 4,
                _item(fmt_ar(r["objectif"]) if r["objectif"] > 0 else "non défini", droite=True))

            # Barre de progression
            self.table.setCellWidget(i, 5, BarreAgent(pct))

            # Fond de ligne coloré selon le seuil
            if pct is not None:
                fond, _ = _fond(pct)
                q = QColor(fond); q.setAlpha(70)
            else:
                q = QColor(P["carte"]); q.setAlpha(0)

            for col in range(5):
                it = self.table.item(i, col)
                if it:
                    it.setBackground(q)
                    it.setForeground(QColor(P["texte"]))

        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 130)

    # ── Sélection ────────────────────────────────────────────────────────────

    def _agent_selectionne(self):
        i = self.table.currentRow()
        if i < 0 or i >= len(self.df):
            return None
        return self.df.iloc[i]

    def selection_changee(self):
        a = self._agent_selectionne()
        if a is not None:
            self.lbl_sel.setText(f"Agent sélectionné : {a['agent']}  —  {a['agence']}")
            self.champ.setText(f"{a['objectif']:.0f}" if a["objectif"] > 0 else "")

    # ── Actions ──────────────────────────────────────────────────────────────

    def enregistrer(self):
        a = self._agent_selectionne()
        if a is None:
            QMessageBox.information(self, "Sélection", "Sélectionnez d'abord un agent."); return
        try:
            valeur = float(self.champ.text().replace(" ", "").replace("\u202f", ""))
            if valeur < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Objectif", "Saisissez un nombre positif (en Ariary)."); return
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE dim_agent SET objectif = %s WHERE id_agent = %s",
                (valeur, int(a["id_agent"])))
        journaliser(self.utilisateur["id"], "objectif_agent", f"{a['agent']} : {valeur:.0f} Ar")
        self.rafraichir()
        afficher_toast(self, f"Objectif enregistré pour {a['agent']}", "succes")

    def repartir(self):
        a = self._agent_selectionne()
        if a is None:
            QMessageBox.information(self, "Sélection",
                "Sélectionnez un agent de l'agence concernée."); return
        obj = pd.read_sql(
            "SELECT COALESCE(objectif,0) AS o FROM dim_agence WHERE id_agence = %(i)s",
            engine, params={"i": int(a["id_agence"])}).iloc[0]["o"]
        nb = int((self.df["id_agence"] == a["id_agence"]).sum())
        if not obj or nb == 0:
            QMessageBox.warning(self, "Répartition",
                "L'agence n'a pas d'objectif défini (écran Agences)."); return
        part = float(obj) / nb
        if QMessageBox.question(
                self, "Confirmer",
                f"Attribuer {part/1e6:,.1f} M Ar à chacun des {nb} agents de {a['agence']} ?"
                .replace(",", " ")) != QMessageBox.Yes:
            return
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE dim_agent SET objectif = %s WHERE id_agence = %s",
                (part, int(a["id_agence"])))
        journaliser(self.utilisateur["id"], "objectif_agence_reparti",
                    f"{a['agence']} : {part:.0f} Ar x {nb}")
        self.rafraichir()
        afficher_toast(self, "Objectifs répartis équitablement", "succes")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _item(texte, droite=False, centre=False):
    from PySide6.QtWidgets import QTableWidgetItem
    it = QTableWidgetItem(str(texte))
    if droite:
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    elif centre:
        it.setTextAlignment(Qt.AlignCenter)
    return it