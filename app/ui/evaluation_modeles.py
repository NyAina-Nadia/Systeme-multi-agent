import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTableWidget,
                               QScrollArea, QFrame)
from app.ui.graphiques import InfoBulle
from app.theme import P, ACCENT, OR, SUCCES, styler_graphique
from app.ui.widgets import TitrePage, Carte, CarteKPI, etiquette, preparer_table, item, badge
from ml.backtest import diagnostic
from ml.modeles import MODELS
from ml.prevision import historique_mensuel_par_agence
from ml.series import serie_agence

MIN_APPRENTISSAGE = 4


class EvaluationModelesScreen(QWidget):
    """Évaluation régulière des prévisions : le modèle retenu reste-t-il adapté à l'évolution des ventes ?"""
    def __init__(self, utilisateur):
        super().__init__()
        self._bulle = None
        self.pivot = historique_mensuel_par_agence()
        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(16); layout.setContentsMargins(0, 0, 10, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        entete = QHBoxLayout()
        entete.addWidget(TitrePage("Suivi des prévisions",
                                   "Backtest glissant : à chaque mois, chaque modèle prévoit le mois suivant, puis on compare au réel"), 1)
        self.combo = QComboBox(); self.combo.setMinimumWidth(180)
        if len(self.pivot):
            self.combo.addItems(list(self.pivot.columns))
        l = QLabel("Agence"); l.setObjectName("sousTitre"); entete.addWidget(l); entete.addWidget(self.combo)
        layout.addLayout(entete)

        self.zone_kpi = QHBoxLayout(); self.zone_kpi.setSpacing(16)
        layout.addLayout(self.zone_kpi)

        self.msg = QLabel(""); self.msg.setObjectName("alerteNeutre"); self.msg.setWordWrap(True)
        layout.addWidget(self.msg)

        carte = Carte(); lc = QVBoxLayout(carte); lc.setContentsMargins(18, 14, 18, 14)
        lc.addWidget(etiquette("Erreur absolue de chaque modèle, mois par mois (M Ar)"))
        self.graphique = pg.PlotWidget(); styler_graphique(self.graphique); self.graphique.setMinimumHeight(300)
        self.graphique.addLegend(offset=(10, 10))
        lc.addWidget(self.graphique)
        layout.addWidget(carte)

        carte2 = Carte(); l2 = QVBoxLayout(carte2); l2.setContentsMargins(18, 14, 18, 14)
        l2.addWidget(etiquette("Synthèse par modèle sur l'ensemble des mois testés"))
        self.table = QTableWidget(); preparer_table(self.table)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Modèle", "MAE (M Ar)", "MAPE (%)", "MAE 3 derniers mois", "Biais (M Ar)"])
        self.table.setMinimumHeight(190)
        l2.addWidget(self.table)
        layout.addWidget(carte2)

        self.combo.currentTextChanged.connect(self.rafraichir)
        self.rafraichir(self.combo.currentText())

    def _vider(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget() is not None:
                it.widget().hide(); it.widget().deleteLater()

    def rafraichir(self, agence):
        if self._bulle is not None:
            self._bulle.detacher(); self._bulle = None
        self.graphique.clear(); self._vider(self.zone_kpi); self.table.setRowCount(0)
        if not agence or not len(self.pivot):
            self.msg.setText("Aucune donnée de vente."); return
        periodes, y = serie_agence(self.pivot, agence)
        if len(y) < MIN_APPRENTISSAGE + 3:
            self.msg.setText(f"Historique insuffisant pour « {agence} » : {len(y)} mois, "
                             f"{MIN_APPRENTISSAGE + 3} sont nécessaires pour un backtest.")
            return
        d = diagnostic(y, MODELS, MIN_APPRENTISSAGE)
        self.msg.setText(d["recommandation"])

        derive = d["derive"]
        ton = SUCCES if (derive is None or derive < d["seuil_derive"]) else ACCENT
        self.zone_kpi.addWidget(CarteKPI("Modèle retenu", d["retenu"], "règle de l'application (3 derniers mois)", P["serie1"], "🧠"))
        self.zone_kpi.addWidget(CarteKPI("Meilleur sur tout l'historique", d["meilleur_global"],
                                         f"{d['n_tests']} mois testés", OR, "🏅"))
        self.zone_kpi.addWidget(CarteKPI("Dérive de l'erreur", "—" if derive is None else f"× {derive:.2f}",
                                         "erreur récente / erreur passée du modèle retenu", ton, "📉"))

        bt = d["backtest"]
        x = list(range(len(bt)))
        couleurs = [P["serie1"], P["serie2"], P["serie3"], "#8E7CC3"]
        for i, nom in enumerate(MODELS):
            col = f"{nom}_err"
            if col in bt:
                ep = 4 if nom == d["retenu"] else 2
                self.graphique.plot(x, bt[col].tolist(), pen=pg.mkPen(couleurs[i % 4], width=ep),
                                    symbol="o", symbolSize=7, symbolBrush=couleurs[i % 4], name=nom + (" ✓" if nom == d["retenu"] else ""))
        etiq = [str(periodes[MIN_APPRENTISSAGE + k])[2:] for k in x]
        self.graphique.getAxis("bottom").setTicks([list(zip(x, etiq))])
        self._bulle = InfoBulle(self.graphique,
                                [(nom, x, bt[f'{nom}_err'].tolist(), couleurs[i % 4]) for i, nom in enumerate(MODELS) if f'{nom}_err' in bt],
                                dict(zip(x, etiq)), fmt=lambda v: f'{v:.1f} M Ar')

        tab = d["tableau"]
        self.table.setRowCount(len(tab))
        for i, r in tab.iterrows():
            self.table.setItem(i, 0, item(r["modele"] + ("   ✓ retenu" if r["modele"] == d["retenu"] else "")))
            self.table.setItem(i, 1, item(f"{r['mae']:.1f}", True))
            self.table.setItem(i, 2, item(f"{r['mape']:.1f}", True))
            self.table.setItem(i, 3, item(f"{r['mae_recent']:.1f}", True))
            self.table.setItem(i, 4, item(f"{r['biais']:+.1f}", True))
        self.table.resizeColumnsToContents()
