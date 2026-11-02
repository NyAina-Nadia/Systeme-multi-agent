
import pandas as pd
import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QTableWidget,
    QScrollArea,
    QFrame,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
)

from app.db import engine
from ml.prevision import prevoir
from app.ui.graphiques import InfoBulle
from app.theme import P, ACCENT, OR, SUCCES, styler_graphique
from app.ui.widgets import (
    TitrePage,
    Carte,
    CarteKPI,
    etiquette,
    preparer_table,
    item,
)


class PrevisionScreen(QWidget):

    def __init__(self, utilisateur):
        super().__init__()

        self.utilisateur = utilisateur
        self._bulle = None
        self._legende = None

        self.setObjectName("page")

        # --------------------------------------------------
        # CONTENEUR PRINCIPAL AVEC DÉFILEMENT
        # --------------------------------------------------
        self.defilement = QScrollArea()
        self.defilement.setWidgetResizable(True)
        self.defilement.setFrameShape(QFrame.Shape.NoFrame)
        self.defilement.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.defilement.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.contenu = QWidget()
        self.contenu.setObjectName("page")

        layout = QVBoxLayout(self.contenu)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)

        self.defilement.setWidget(self.contenu)

        ext = QVBoxLayout(self)
        ext.setContentsMargins(0, 0, 0, 0)
        ext.addWidget(self.defilement)

        # --------------------------------------------------
        # EN-TÊTE ET FILTRES
        # --------------------------------------------------
        entete = QHBoxLayout()
        entete.setSpacing(14)

        titre = TitrePage(
            "Prévision commerciale",
            "Anticipez l'évolution du chiffre d'affaires "
            "et comparez les performances des modèles prédictifs."
        )
        entete.addWidget(titre, 1)

        filtres = QHBoxLayout()
        filtres.setSpacing(8)

        self.combo_agence = QComboBox()
        self.combo_agence.setMinimumWidth(170)
        self.combo_agence.setMinimumHeight(40)
        self.combo_agence.setToolTip(
            "Choisir l'agence à analyser"
        )

        self.combo_horizon = QComboBox()
        self.combo_horizon.addItem("3 mois", 3)
        self.combo_horizon.addItem("6 mois", 6)
        self.combo_horizon.setMinimumWidth(105)
        self.combo_horizon.setMinimumHeight(40)
        self.combo_horizon.setToolTip(
            "Choisir la durée de la prévision"
        )

        for libelle, widget in (
            ("Agence", self.combo_agence),
            ("Horizon", self.combo_horizon),
        ):
            label = QLabel(libelle)
            label.setObjectName("sousTitre")
            filtres.addWidget(label)
            filtres.addWidget(widget)

        entete.addLayout(filtres)
        layout.addLayout(entete)

        # --------------------------------------------------
        # MESSAGE D'INFORMATION
        # --------------------------------------------------
        self.msg = QLabel("")
        self.msg.setObjectName("alerteNeutre")
        self.msg.setWordWrap(True)
        self.msg.setContentsMargins(14, 12, 14, 12)
        self.msg.hide()

        layout.addWidget(self.msg)

        # --------------------------------------------------
        # INDICATEURS KPI
        # --------------------------------------------------
        self.zone_kpi = QHBoxLayout()
        self.zone_kpi.setSpacing(16)
        layout.addLayout(self.zone_kpi)

        # --------------------------------------------------
        # CARTE DU GRAPHIQUE
        # --------------------------------------------------
        self.carte_graphique = self._creer_carte(
            "Évolution du chiffre d'affaires",
            "Historique des ventes et estimation du chiffre "
            "d'affaires mensuel. La zone colorée représente "
            "l'intervalle de prévision à 80 %."
        )

        lc = self.carte_graphique.layout()

        self.graphique = pg.PlotWidget()
        styler_graphique(self.graphique)

        self.graphique.setMinimumHeight(350)
        self.graphique.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.graphique.setMenuEnabled(False)
        self.graphique.setMouseEnabled(x=True, y=False)
        self.graphique.showGrid(x=False, y=True, alpha=0.20)

        self.graphique.setLabel(
            "left",
            "Chiffre d'affaires",
            units="M Ar",
            color=P["doux"],
        )
        self.graphique.setLabel(
            "bottom",
            "Période",
            color=P["doux"],
        )

        self._configurer_axes(self.graphique)

        lc.addWidget(self.graphique)
        layout.addWidget(self.carte_graphique)

        # --------------------------------------------------
        # LÉGENDE PERSONNALISÉE
        # --------------------------------------------------
        self.legende = QHBoxLayout()
        self.legende.setSpacing(20)
        self.legende.addStretch()

        layout.addLayout(self.legende)

        # --------------------------------------------------
        # CARTE DE COMPARAISON DES MODÈLES
        # --------------------------------------------------
        self.carte_erreurs = self._creer_carte(
            "Évaluation des modèles prédictifs",
            "Comparaison des erreurs sur les trois derniers "
            "mois connus. Une erreur plus faible indique "
            "généralement une meilleure précision sur cette période."
        )

        l2 = self.carte_erreurs.layout()

        self.table_erreurs = QTableWidget()
        preparer_table(self.table_erreurs)

        self.table_erreurs.setColumnCount(3)
        self.table_erreurs.setHorizontalHeaderLabels([
            "Modèle prédictif",
            "Erreur MAE (M Ar)",
            "Erreur MAPE (%)",
        ])

        self._configurer_table()

        l2.addWidget(self.table_erreurs)
        layout.addWidget(self.carte_erreurs)

        layout.addStretch()

        # --------------------------------------------------
        # CHARGEMENT ET ÉVÉNEMENTS
        # --------------------------------------------------
        self.charger_agences()

        self.combo_agence.currentTextChanged.connect(
            self.rafraichir
        )

        self.combo_horizon.currentIndexChanged.connect(
            lambda _: self.rafraichir(
                self.combo_agence.currentText()
            )
        )

        if self.combo_agence.count() > 0:
            self.rafraichir(self.combo_agence.currentText())
        else:
            self._afficher_message(
                "Aucune agence disponible. "
                "Ajoutez une agence avant de lancer une prévision."
            )

    # ======================================================
    # CRÉATION DES CARTES
    # ======================================================
    def _creer_carte(self, titre, description=None):
        carte = Carte()

        carte.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        layout = QVBoxLayout(carte)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(etiquette(titre))

        if description:
            texte = QLabel(description)
            texte.setWordWrap(True)
            texte.setStyleSheet(
                f"color: {P['doux']}; "
                "font-size: 11px; "
                "background: transparent;"
            )
            layout.addWidget(texte)

        return carte

    # ======================================================
    # CONFIGURATION DU GRAPHIQUE
    # ======================================================
    def _configurer_axes(self, graphique):
        for nom in ("left", "bottom"):
            axe = graphique.getAxis(nom)
            axe.setPen(P["grille"])
            axe.setTextPen(P["doux"])
            axe.setStyle(
                tickFont=QFont("Segoe UI", 9)
            )

        graphique.getAxis("bottom").setHeight(45)

    # ======================================================
    # CONFIGURATION DU TABLEAU
    # ======================================================
    def _configurer_table(self):
        table = self.table_erreurs

        table.setMinimumHeight(220)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)

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

        entete = table.horizontalHeader()
        entete.setMinimumHeight(42)
        entete.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    # ======================================================
    # CHARGEMENT DES AGENCES
    # ======================================================
    def charger_agences(self):
        try:
            df = pd.read_sql(
                "SELECT agence FROM dim_agence ORDER BY agence",
                engine,
            )

            self.combo_agence.clear()

            if not df.empty:
                self.combo_agence.addItems(
                    df["agence"].dropna().astype(str).tolist()
                )

        except Exception as erreur:
            self._afficher_message(
                "Impossible de charger les agences. "
                "Vérifiez la connexion à la base de données."
            )
            print(
                f"Erreur de chargement des agences : {erreur}"
            )

    # ======================================================
    # VIDAGE DES KPI
    # ======================================================
    def _vider(self, layout):
        while layout.count():
            element = layout.takeAt(0)

            widget = element.widget()

            if widget is not None:
                widget.setParent(None)

            elif element.layout() is not None:
                self._vider(element.layout())

    # ======================================================
    # LÉGENDE
    # ======================================================
    def _ajouter_legende(self, couleur, texte):
        groupe = QHBoxLayout()
        groupe.setSpacing(7)

        point = QFrame()
        point.setFixedSize(10, 10)
        point.setStyleSheet(
            f"background-color: {couleur}; "
            "border-radius: 5px;"
        )

        label = QLabel(texte)
        label.setStyleSheet(
            f"color: {P['doux']}; "
            "font-size: 11px; "
            "background: transparent;"
        )

        groupe.addWidget(point)
        groupe.addWidget(label)

        self.legende.addLayout(groupe)

    def _actualiser_legende(self):
        self._vider(self.legende)

        self._ajouter_legende(
            P["serie1"],
            "Historique réel",
        )
        self._ajouter_legende(
            P["serie2"],
            "Prévision",
        )

        groupe = QHBoxLayout()
        groupe.setSpacing(7)

        zone = QFrame()
        zone.setFixedSize(18, 10)

        couleur = QColor(P["serie2"])
        couleur.setAlpha(65)

        zone.setStyleSheet(
            f"background-color: {couleur.name()}; "
            "border-radius: 3px;"
        )

        texte = QLabel("Intervalle à 80 %")
        texte.setStyleSheet(
            f"color: {P['doux']}; "
            "font-size: 11px; "
            "background: transparent;"
        )

        groupe.addWidget(zone)
        groupe.addWidget(texte)

        self.legende.addLayout(groupe)
        self.legende.addStretch()

    # ======================================================
    # MESSAGES D'INFORMATION
    # ======================================================
    def _afficher_message(self, texte):
        self.msg.setText(texte)
        self.msg.show()

    # ======================================================
    # RAFRAÎCHISSEMENT GÉNÉRAL
    # ======================================================
    def rafraichir(self, agence):
        if not agence:
            return

        # Détacher l'ancienne infobulle avant de
        # reconstruire le graphique.
        if self._bulle is not None:
            self._bulle.detacher()
            self._bulle = None

        self.graphique.clear()
        self._vider(self.zone_kpi)
        self.table_erreurs.setRowCount(0)
        self.msg.hide()

        horizon = self.combo_horizon.currentData() or 3

        try:
            resultat = prevoir(agence, horizon)
        except Exception as erreur:
            self._afficher_message(
                "Une erreur est survenue pendant la prévision. "
                "Vérifiez les données de l'agence et le terminal "
                "pour consulter le détail."
            )
            print(f"Erreur de prévision : {erreur}")
            return

        if resultat is None:
            self._afficher_message(
                "Historique insuffisant pour cette agence. "
                "Il faut au moins 6 mois de ventes pour "
                "effectuer une prévision."
            )
            return

        hist = list(resultat["historique"])
        prev = list(resultat["prevision"])

        if not hist or not prev:
            self._afficher_message(
                "Les données historiques ou les prévisions "
                "sont vides pour cette agence."
            )
            return

        # --------------------------------------------------
        # GRAPHIQUE : HISTORIQUE ET PRÉVISION
        # --------------------------------------------------
        n = len(hist)

        x_hist = list(range(n))
        x_prev = list(range(n, n + len(prev)))
        x_ligne = [n - 1] + x_prev

        historique = self.graphique.plot(
            x_hist,
            hist,
            pen=pg.mkPen(P["serie1"], width=3),
            name="Historique",
            symbol="o",
            symbolSize=8,
            symbolBrush=P["serie1"],
            symbolPen=pg.mkPen(P["carte"], width=1.5),
        )

        # Préparer les bornes pour la zone d'incertitude.
        valeurs_basses = (
            [hist[-1]] + list(resultat["borne_basse"])
        )
        valeurs_hautes = (
            [hist[-1]] + list(resultat["borne_haute"])
        )

        bas = pg.PlotDataItem(
            x_ligne,
            valeurs_basses,
        )
        haut = pg.PlotDataItem(
            x_ligne,
            valeurs_hautes,
        )

        couleur_zone = QColor(P["serie2"])
        couleur_zone.setAlpha(55)

        self.graphique.addItem(
            pg.FillBetweenItem(
                bas,
                haut,
                brush=couleur_zone,
            )
        )

        # Les courbes doivent être ajoutées au graphique
        # pour que la zone remplie puisse les utiliser.
        self.graphique.addItem(bas)
        self.graphique.addItem(haut)

        self.graphique.plot(
            x_ligne,
            [hist[-1]] + prev,
            pen=pg.mkPen(
                P["serie2"],
                width=3,
                style=Qt.PenStyle.DashLine,
            ),
            symbol="o",
            symbolSize=9,
            symbolBrush=P["serie2"],
            symbolPen=pg.mkPen(P["carte"], width=1.5),
            name="Prévision",
        )

        self.graphique.setLabel(
            "left",
            "Chiffre d'affaires",
            units="M Ar",
            color=P["doux"],
        )
        self.graphique.setLabel(
            "bottom",
            "Période",
            color=P["doux"],
        )

        periodes = (
            list(resultat["periodes_historique"])
            + list(resultat["periodes_prevision"])
        )

        pas = 1 if len(periodes) <= 12 else 2

        self.graphique.getAxis("bottom").setTicks([
            [
                (i, str(periode)[2:])
                for i, periode in enumerate(periodes)
                if i % pas == 0
            ]
        ])

        self._configurer_axes(self.graphique)
        self._actualiser_legende()

        # --------------------------------------------------
        # INFOBULLE INTERACTIVE
        # --------------------------------------------------
        def intervalle(x, r=resultat, debut=n):
            k = int(round(x)) - debut

            bornes_basses = r["borne_basse"]
            bornes_hautes = r["borne_haute"]

            if 0 <= k < len(r["prevision"]):
                basse = bornes_basses[k]
                haute = bornes_hautes[k]

                return (
                    "Intervalle à 80 % : "
                    f"{basse:,.0f} – {haute:,.0f} M Ar"
                ).replace(",", " ")

            return ""

        self._bulle = InfoBulle(
            self.graphique,
            [
                (
                    "Historique",
                    x_hist,
                    hist,
                    P["serie1"],
                ),
                (
                    "Prévision",
                    x_prev,
                    prev,
                    P["serie2"],
                ),
            ],
            dict(enumerate(periodes)),
            fmt=lambda valeur: (
                f"{valeur:,.0f} M Ar".replace(",", " ")
            ),
            extra=intervalle,
        )

        # --------------------------------------------------
        # KPI : RÉSULTATS DE LA PRÉVISION
        # --------------------------------------------------
        total_prev = sum(prev)
        total_hist = sum(hist[-horizon:])

        variation = (
            (total_prev / total_hist - 1) * 100
            if total_hist
            else None
        )

        modele_retenu = resultat["modele_retenu"]
        mape = resultat["erreurs_mape"].get(modele_retenu)

        fiable = (
            "Fiabilité correcte"
            if mape is not None and mape < 15
            else "Fiabilité limitée"
        )

        couleur_fiabilite = (
            SUCCES
            if mape is not None and mape < 15
            else OR
        )

        self.zone_kpi.addWidget(
            CarteKPI(
                "MODÈLE RETENU",
                str(modele_retenu),
                "Meilleure erreur de test",
                P["serie1"],
                "",
            )
        )

        self.zone_kpi.addWidget(
            CarteKPI(
                f"CA PRÉVU · {horizon} MOIS",
                f"{total_prev:,.0f} M Ar".replace(",", " "),
                f"Comparaison avec les {horizon} derniers mois",
                ACCENT,
                "↗",
                variation,
            )
        )

        self.zone_kpi.addWidget(
            CarteKPI(
                "ERREUR MOYENNE · MAPE",
                f"{mape:.1f} %" if mape is not None else "—",
                fiable,
                couleur_fiabilite,
                "%",
            )
        )

        # --------------------------------------------------
        # TABLEAU COMPARATIF DES MODÈLES
        # --------------------------------------------------
        erreurs_mae = resultat["erreurs_mae"]
        erreurs_mape = resultat["erreurs_mape"]

        self.table_erreurs.setRowCount(len(erreurs_mae))

        for i, (modele, erreur) in enumerate(
            erreurs_mae.items()
        ):
            retenu = modele == modele_retenu

            nom = str(modele)
            if retenu:
                nom += "  ✓ Retenu"

            self.table_erreurs.setItem(
                i,
                0,
                item(nom),
            )

            self.table_erreurs.setItem(
                i,
                1,
                item(f"{erreur:.2f}", True),
            )

            valeur_mape = erreurs_mape.get(modele)

            self.table_erreurs.setItem(
                i,
                2,
                item(
                    f"{valeur_mape:.2f}"
                    if valeur_mape is not None
                    else "—",
                    True,
                ),
            )

        self.table_erreurs.resizeRowsToContents()
