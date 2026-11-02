import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSlider, QSpinBox,
                               QLineEdit, QScrollArea, QFrame, QFormLayout)
from PySide6.QtCore import Qt
from app.db import engine
from app.ui.graphiques import InfoBulle
from app.theme import P, ACCENT, OR, SUCCES, styler_graphique
from app.ui.widgets import TitrePage, Carte, CarteKPI, etiquette
from ml.prevision import historique_mensuel_par_agence
from ml.scenarios import projeter


class ScenariosScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self._bulle = None
        self.pivot = historique_mensuel_par_agence()
        self.objectifs = pd.read_sql("SELECT agence, COALESCE(objectif,0) AS objectif FROM dim_agence", engine)\
                           .set_index("agence")["objectif"].astype(float).to_dict()

        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(16); layout.setContentsMargins(0, 0, 10, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        layout.addWidget(TitrePage("Scénarios « et si ? »",
                                   "Simulez l'effet d'une hausse des volumes ou des prix sur l'atteinte de l'objectif"))

        # ---- Paramètres ----
        carte = Carte(); lp = QVBoxLayout(carte); lp.setContentsMargins(18, 14, 18, 14)
        lp.addWidget(etiquette("Paramètres du scénario"))
        form = QFormLayout(); form.setHorizontalSpacing(18)
        self.combo = QComboBox(); self.combo.addItem("Toutes les agences")
        self.combo.addItems(list(self.pivot.columns))
        self.s_volume, self.l_volume = self._slider(-30, 50)
        self.s_prix, self.l_prix = self._slider(-20, 30)
        self.horizon = QSpinBox(); self.horizon.setRange(1, 12); self.horizon.setValue(3); self.horizon.setSuffix(" mois")
        self.objectif = QLineEdit(); self.objectif.setPlaceholderText("Objectif en M Ar")
        form.addRow("Périmètre", self.combo)
        form.addRow("Variation des volumes", self._ligne(self.s_volume, self.l_volume))
        form.addRow("Variation des prix", self._ligne(self.s_prix, self.l_prix))
        form.addRow("Horizon de projection", self.horizon)
        form.addRow("Objectif à atteindre (M Ar)", self.objectif)
        lp.addLayout(form)
        note = QLabel("Hypothèse : le rythme actuel est la moyenne des 3 derniers mois. Le scénario le multiplie par "
                      "(1 + variation des volumes) × (1 + variation des prix) pour chaque mois projeté.")
        note.setObjectName("sousTitre"); note.setWordWrap(True); lp.addWidget(note)
        layout.addWidget(carte)

        self.zone_kpi = QHBoxLayout(); self.zone_kpi.setSpacing(16)
        layout.addLayout(self.zone_kpi)

        carte2 = Carte(); l2 = QVBoxLayout(carte2); l2.setContentsMargins(18, 14, 18, 14)
        l2.addWidget(etiquette("CA cumulé (M Ar) : trajectoire actuelle, scénario et objectif"))
        self.graphique = pg.PlotWidget(); styler_graphique(self.graphique); self.graphique.setMinimumHeight(320)
        self.graphique.addLegend(offset=(10, 10))
        l2.addWidget(self.graphique)
        layout.addWidget(carte2)
        self.msg = QLabel(""); self.msg.setObjectName("alerteNeutre"); self.msg.setWordWrap(True); self.msg.hide()
        layout.addWidget(self.msg)

        self.combo.currentIndexChanged.connect(self._perimetre_change)
        self.s_volume.valueChanged.connect(self.rafraichir); self.s_prix.valueChanged.connect(self.rafraichir)
        self.horizon.valueChanged.connect(self.rafraichir); self.objectif.editingFinished.connect(self.rafraichir)
        self._perimetre_change()

    def _slider(self, mini, maxi):
        s = QSlider(Qt.Horizontal); s.setRange(mini, maxi); s.setValue(0); s.setMinimumWidth(260)
        l = QLabel("0 %"); l.setMinimumWidth(52)
        s.valueChanged.connect(lambda v, lab=l: lab.setText(f"{v:+d} %"))
        return s, l

    def _ligne(self, slider, label):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.addWidget(slider, 1); h.addWidget(label)
        return w

    def _serie(self):
        nom = self.combo.currentText()
        if nom == "Toutes les agences":
            return self.pivot.sum(axis=1).tolist(), sum(self.objectifs.get(a, 0) for a in self.pivot.columns) / 1e6
        return self.pivot[nom].tolist(), self.objectifs.get(nom, 0) / 1e6

    def _perimetre_change(self):
        _, obj = self._serie()
        self.objectif.setText(f"{obj:.0f}")
        self.rafraichir()

    def _vider(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)

    def rafraichir(self, *_):
        serie, _ = self._serie()
        if self._bulle is not None:
            self._bulle.detacher(); self._bulle = None
        self.graphique.clear(); self._vider(self.zone_kpi)
        if len(serie) < 3:
            self.msg.setText("Historique insuffisant (3 mois minimum)."); self.msg.show(); return
        self.msg.hide()
        try:
            objectif = float(self.objectif.text().replace(" ", "") or 0)
        except ValueError:
            objectif = 0.0
        h = self.horizon.value()
        r = projeter(serie, objectif, self.s_volume.value(), self.s_prix.value(), h)

        n = r["n_historique"]
        x = list(range(n + h))
        self.graphique.plot(x, r["serie_base"], pen=pg.mkPen(P["serie1"], width=3), name="Trajectoire actuelle")
        self.graphique.plot(x, r["serie_scenario"], pen=pg.mkPen(P["serie2"], width=3), name="Scénario")
        if objectif > 0:
            ligne = pg.InfiniteLine(pos=objectif, angle=0, pen=pg.mkPen(P["serie3"], width=2, style=Qt.PenStyle.DashLine),
                                    label="Objectif", labelOpts={"color": P["serie3"], "position": 0.08})
            self.graphique.addItem(ligne)
        etiq = {i: (f"Mois {i+1}" if i < n else f"Projection +{i-n+1}") for i in x}
        self.graphique.getAxis("bottom").setTicks([[(i, f"M{i+1}" if i < n else f"+{i-n+1}") for i in x]])
        self._bulle = InfoBulle(self.graphique,
                                [('Trajectoire actuelle', x, r['serie_base'], P['serie1']), ('Scénario', x, r['serie_scenario'], P['serie2'])],
                                etiq, fmt=lambda v: f'{v:,.0f} M Ar'.replace(',', ' '))

        ts = r["taux_atteinte_scenario"]
        gain = r["gain_scenario"]
        self.zone_kpi.addWidget(CarteKPI("CA cumulé du scénario", f"{r['cumul_scenario']:,.0f} M Ar".replace(",", " "),
                                         f"base : {r['cumul_base']:,.0f} M Ar".replace(",", " "), P["serie2"], "🔮"))
        self.zone_kpi.addWidget(CarteKPI("Gain vs trajectoire actuelle", f"{gain:+,.0f} M Ar".replace(",", " "),
                                         "sur l'horizon choisi", SUCCES if gain >= 0 else ACCENT, "💹"))
        self.zone_kpi.addWidget(CarteKPI("Atteinte de l'objectif", f"{ts:.0f} %" if ts is not None else "—",
                                         f"sans action : {r['taux_atteinte_base']:.0f} %" if ts is not None else "objectif non défini",
                                         SUCCES if (ts or 0) >= 100 else OR, "🎯"))
        hr = r["hausse_requise_pct"]
        texte = "—" if objectif <= 0 else ("déjà atteint" if hr <= 0 else f"+{hr:.0f} %")
        self.zone_kpi.addWidget(CarteKPI("Effort requis", texte, "hausse du rythme mensuel pour atteindre l'objectif",
                                         ACCENT, "⛰"))
