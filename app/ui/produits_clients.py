
import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QLabel, QScrollArea, QFrame,
    QHeaderView, QAbstractItemView, QSizePolicy
)

from app.theme import P, ACCENT, OR, SUCCES, styler_graphique
from app.ui.widgets import (
    TitrePage, Carte, CarteKPI, etiquette,
    preparer_table, item, badge, fmt_ar
)
from ml.abc_rfm import analyse_abc, segmentation_rfm


COULEUR_CLASSE = {
    "A": SUCCES,
    "B": OR,
    "C": ACCENT
}

BADGE_CLASSE = {
    "A": "vert",
    "B": "ambre",
    "C": "rouge"
}


class ProduitsClientsScreen(QWidget):

    def __init__(self, utilisateur):
        super().__init__()

        self.utilisateur = utilisateur
        self.setObjectName("page")

        # --------------------------------------------------
        # CONTENEUR PRINCIPAL
        # --------------------------------------------------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(20)

        # En-tête de la page
        layout.addWidget(
            TitrePage(
                "Produits & Clients",
                "Analyse des performances produits et "
                "compréhension du comportement client"
            )
        )

        # --------------------------------------------------
        # ONGLETS
        # --------------------------------------------------
        self.onglets = QTabWidget()
        self.onglets.setObjectName("ongletsAnalyse")
        self.onglets.setDocumentMode(True)
        self.onglets.setMovable(False)
        self.onglets.setUsesScrollButtons(True)
        self.onglets.setElideMode(Qt.TextElideMode.ElideRight)

        self.onglets.addTab(
            self._onglet_abc(),
            "  ◈  Analyse ABC"
        )

        self.onglets.addTab(
            self._onglet_rfm(),
            "  ◉  Segmentation RFM"
        )

        layout.addWidget(self.onglets, 1)

    # ======================================================
    # OUTILS GRAPHIQUES ET INTERFACE
    # ======================================================

    def _creer_page(self):
        """Page défilante avec marges et espacements réguliers."""
        page = QWidget()
        page.setObjectName("page")

        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 16, 8, 20)
        lay.setSpacing(20)

        return page, lay

    def _creer_carte(self, titre, description=None):
        """Carte réutilisant le thème global de l'application."""
        carte = Carte()
        carte.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        lay = QVBoxLayout(carte)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(12)

        lay.addWidget(etiquette(titre))

        if description:
            texte = QLabel(description)
            texte.setWordWrap(True)
            texte.setStyleSheet(
                "color: %s; font-size: 11px; background: transparent;"
                % P["doux"]
            )
            lay.addWidget(texte)

        return carte, lay

    def _page_defilante(self, page):
        """Ajoute un défilement vertical à une page."""
        defil = QScrollArea()
        defil.setWidgetResizable(True)
        defil.setFrameShape(QFrame.Shape.NoFrame)
        defil.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        defil.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        defil.setWidget(page)

        return defil

    def _message_vide(self, titre, description):
        """Affiche un état vide propre si aucune donnée n'existe."""
        page, lay = self._creer_page()

        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icone = QLabel("◈")
        icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icone.setStyleSheet(
            f"color: {P['serie1']}; font-size: 38px;"
            "background: transparent;"
        )

        label_titre = QLabel(titre)
        label_titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_titre.setWordWrap(True)
        label_titre.setStyleSheet(
            f"color: {P['titre']}; font-size: 17px;"
            "font-weight: 800; background: transparent;"
        )

        label_description = QLabel(description)
        label_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_description.setWordWrap(True)
        label_description.setMaximumWidth(520)
        label_description.setStyleSheet(
            f"color: {P['doux']}; font-size: 12px;"
            "background: transparent;"
        )

        lay.addWidget(icone)
        lay.addWidget(label_titre)
        lay.addWidget(label_description)

        return self._page_defilante(page)

    def _creer_graphique(self, hauteur=310):
        """Graphique cohérent avec le thème PyQtGraph de l'application."""
        graph = pg.PlotWidget()
        styler_graphique(graph)

        graph.setMinimumHeight(hauteur)
        graph.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        graph.setMenuEnabled(False)
        graph.setMouseEnabled(x=True, y=False)
        graph.setBackground(P["carte"])
        graph.showGrid(x=False, y=True, alpha=0.20)

        for axe_nom in ("left", "bottom"):
            axe = graph.getAxis(axe_nom)
            axe.setPen(P["grille"])
            axe.setTextPen(P["doux"])
            axe.setStyle(tickFont=QFont("Segoe UI", 9))

        return graph

    def _preparer_table_analyse(self, table, hauteur=280):
        """Tableau moderne utilisant le style global de theme.py."""
        preparer_table(table)

        table.setMinimumHeight(hauteur)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)

        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)

        table.horizontalHeader().setMinimumHeight(42)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        table.horizontalHeader().setStretchLastSection(True)

        # Les couleurs restent gérées par le QSS global.
        # Aucun style local ne bloque le thème clair/sombre.

    # ======================================================
    # ONGLET 1 — ANALYSE ABC
    # ======================================================

    def _onglet_abc(self):

        page, lay = self._creer_page()

        abc = analyse_abc()

        if abc is None or abc.empty:
            return self._message_vide(
                "Aucune vente disponible",
                "Importez des données de vente pour visualiser "
                "la répartition ABC de vos produits."
            )

        abc = abc.reset_index(drop=True)

        # --------------------------------------------------
        # 1. INDICATEURS KPI
        # --------------------------------------------------
        nb = abc["classe"].value_counts()

        part_a = (
            abc.loc[abc["classe"] == "A", "part"].sum() * 100
        )

        kpi = QHBoxLayout()
        kpi.setSpacing(16)

        kpi.addWidget(
            CarteKPI(
                "PRODUITS CLASSE A",
                str(int(nb.get("A", 0))),
                f"{part_a:.1f} % du CA",
                SUCCES,
                "★"
            )
        )

        kpi.addWidget(
            CarteKPI(
                "PRODUITS CLASSE B",
                str(int(nb.get("B", 0))),
                "Contribution intermédiaire",
                OR,
                "◐"
            )
        )

        kpi.addWidget(
            CarteKPI(
                "PRODUITS CLASSE C",
                str(int(nb.get("C", 0))),
                "Contribution complémentaire",
                ACCENT,
                "▽"
            )
        )

        lay.addLayout(kpi)

        # --------------------------------------------------
        # 2. LÉGENDE DES CLASSES
        # --------------------------------------------------
        bandeau = QHBoxLayout()
        bandeau.setSpacing(18)

        for classe, description in (
            ("A", "Prioritaires"),
            ("B", "Intermédiaires"),
            ("C", "Secondaires")
        ):
            groupe = QHBoxLayout()
            groupe.setSpacing(7)

            point = QFrame()
            point.setFixedSize(10, 10)
            point.setStyleSheet(
                "background-color: %s; border-radius: 5px;"
                % COULEUR_CLASSE[classe]
            )

            label = QLabel(f"Classe {classe} · {description}")
            label.setStyleSheet(
                f"color: {P['doux']}; font-size: 11px;"
                "background: transparent;"
            )

            groupe.addWidget(point)
            groupe.addWidget(label)
            bandeau.addLayout(groupe)

        bandeau.addStretch()
        lay.addLayout(bandeau)

        # --------------------------------------------------
        # 3. GRAPHIQUE ABC
        # --------------------------------------------------
        carte, lc = self._creer_carte(
            "Performance commerciale des produits",
            "Chiffre d'affaires en millions d'ariary, "
            "avec une couleur par classe ABC."
        )

        graph = self._creer_graphique(330)

        x = np.arange(len(abc))
        ca = abc["ca"].to_numpy(dtype=float) / 1e6

        for classe in ("A", "B", "C"):
            masque = (
                abc["classe"] == classe
            ).to_numpy()

            if masque.any():
                couleur = COULEUR_CLASSE[classe]

                graph.addItem(
                    pg.BarGraphItem(
                        x=x[masque],
                        height=ca[masque],
                        width=0.62,
                        brush=couleur,
                        pen=pg.mkPen(couleur, width=0.5)
                    )
                )

        graph.setLabel(
            "left",
            "Chiffre d'affaires",
            units="M Ar",
            color=P["doux"]
        )

        graph.setLabel(
            "bottom",
            "Produits",
            color=P["doux"]
        )

        graph.getAxis("bottom").setTicks([
            [
                (int(i), str(produit)[:12])
                for i, produit in zip(x, abc["produit"])
            ]
        ])

        graph.getAxis("bottom").setHeight(65)

        lc.addWidget(graph)
        lay.addWidget(carte)

        # --------------------------------------------------
        # 4. TABLEAU DES PRODUITS
        # --------------------------------------------------
        carte2, l2 = self._creer_carte(
            "Détail des produits",
            "Retrouvez le chiffre d'affaires, la contribution "
            "individuelle et le cumul de chaque produit."
        )

        table = QTableWidget()
        self._preparer_table_analyse(table, 310)

        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Produit",
            "Classe ABC",
            "Chiffre d'affaires",
            "Part du CA",
            "Cumul du CA"
        ])
        table.setRowCount(len(abc))

        for i, r in abc.iterrows():

            classe = str(r["classe"])

            table.setItem(
                i, 0,
                item(str(r["produit"]))
            )

            table.setCellWidget(
                i, 1,
                badge(
                    classe,
                    BADGE_CLASSE.get(classe, "gris")
                )
            )

            table.setItem(
                i, 2,
                item(fmt_ar(r["ca"]), True)
            )

            table.setItem(
                i, 3,
                item(f"{r['part'] * 100:.1f} %", True)
            )

            table.setItem(
                i, 4,
                item(f"{r['cumul'] * 100:.1f} %", True)
            )

        table.setColumnWidth(0, 190)
        table.setColumnWidth(1, 115)
        table.setColumnWidth(2, 185)
        table.setColumnWidth(3, 115)
        table.setColumnWidth(4, 115)

        l2.addWidget(table)
        lay.addWidget(carte2)

        lay.addStretch()

        return self._page_defilante(page)

    # ======================================================
    # ONGLET 2 — SEGMENTATION RFM
    # ======================================================

    def _onglet_rfm(self):

        page, lay = self._creer_page()

        rfm = segmentation_rfm(3)

        if rfm is None or rfm.empty:
            return self._message_vide(
                "Aucun client à analyser",
                "Vérifiez que vos ventes comportent des dates "
                "et des identifiants clients cohérents."
            )

        rfm = rfm.copy()

        # --------------------------------------------------
        # 1. ALERTE FRÉQUENCE
        # --------------------------------------------------
        if not rfm.attrs.get("frequence_exploitable", True):

            info = QLabel(
                "ℹ  Fréquence d'achat peu discriminante : "
                "presque tous les clients n'ont acheté qu'une fois. "
                "La segmentation repose principalement sur le montant "
                "et la récence. Vérifiez la stabilité des identifiants "
                "clients entre les différentes ventes."
            )

            info.setObjectName("alerteNeutre")
            info.setWordWrap(True)
            info.setContentsMargins(14, 12, 14, 12)

            lay.addWidget(info)

        # --------------------------------------------------
        # 2. ORDRE ET COULEURS DES SEGMENTS
        # --------------------------------------------------
        segments = sorted(
            rfm["segment"].dropna().unique(),
            key=lambda seg: rfm.loc[
                rfm["segment"] == seg, "montant"
            ].mean()
        )

        palette = [
            P["serie1"],
            P["serie2"],
            P["serie3"]
        ]

        couleurs = {
            seg: palette[i % len(palette)]
            for i, seg in enumerate(segments)
        }

        resume = (
            rfm.groupby("segment")
            .agg(
                clients=("client", "size"),
                montant_moyen=("montant", "mean"),
                recence=("recence", "mean"),
                frequence=("frequence", "mean"),
                ca=("montant", "sum")
            )
            .reindex(segments)
        )

        ca_total = float(rfm["montant"].sum())

        # --------------------------------------------------
        # 3. KPI DES SEGMENTS
        # --------------------------------------------------
        kpi = QHBoxLayout()
        kpi.setSpacing(16)

        for seg, r in resume.iterrows():

            part_ca = (
                float(r["ca"]) / ca_total * 100
                if ca_total > 0 else 0
            )

            kpi.addWidget(
                CarteKPI(
                    str(seg),
                    f"{int(r['clients']):,}".replace(",", " "),
                    f"{part_ca:.1f} % du CA",
                    couleurs[seg],
                    "●"
                )
            )

        lay.addLayout(kpi)

        # --------------------------------------------------
        # 4. GRAPHIQUE RFM
        # --------------------------------------------------
        carte, lc = self._creer_carte(
            "Cartographie du portefeuille clients",
            "Chaque point représente un client. Une récence faible "
            "indique un achat plus récent ; un montant élevé indique "
            "une contribution financière plus importante."
        )

        graph = self._creer_graphique(350)
        graph.addLegend(
            offset=(12, 12),
            labelTextColor=P["texte"]
        )

        for seg in segments:

            d = rfm[rfm["segment"] == seg]

            couleur = QColor(couleurs[seg])
            couleur.setAlpha(180)

            graph.addItem(
                pg.ScatterPlotItem(
                    x=d["recence"].to_numpy(dtype=float),
                    y=d["montant"].to_numpy(dtype=float) / 1e6,
                    size=9,
                    brush=couleur,
                    pen=pg.mkPen(couleurs[seg], width=0.8),
                    name=str(seg)
                )
            )

        graph.setLabel(
            "bottom",
            "Récence",
            units="jours",
            color=P["doux"]
        )

        graph.setLabel(
            "left",
            "Montant total",
            units="M Ar",
            color=P["doux"]
        )

        lc.addWidget(graph)
        lay.addWidget(carte)

        # --------------------------------------------------
        # 5. TABLEAU DES PROFILS
        # --------------------------------------------------
        carte2, l2 = self._creer_carte(
            "Comparaison des segments",
            "Analysez le nombre de clients, leur valeur moyenne "
            "et leur fréquence d'achat."
        )

        table = QTableWidget()
        self._preparer_table_analyse(table, 245)

        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Segment client",
            "Nombre de clients",
            "Montant moyen",
            "Récence moyenne",
            "Achats moyens"
        ])
        table.setRowCount(len(resume))

        for i, (seg, r) in enumerate(resume.iterrows()):

            table.setItem(
                i, 0,
                item(str(seg))
            )

            table.setItem(
                i, 1,
                item(
                    f"{int(r['clients']):,}".replace(",", " "),
                    True
                )
            )

            table.setItem(
                i, 2,
                item(fmt_ar(r["montant_moyen"], False), True)
            )

            table.setItem(
                i, 3,
                item(f"{r['recence']:.0f} jours", True)
            )

            table.setItem(
                i, 4,
                item(f"{r['frequence']:.1f}", True)
            )

        table.setColumnWidth(0, 185)
        table.setColumnWidth(1, 140)
        table.setColumnWidth(2, 175)
        table.setColumnWidth(3, 145)
        table.setColumnWidth(4, 125)

        l2.addWidget(table)
        lay.addWidget(carte2)

        lay.addStretch()

        return self._page_defilante(page)
