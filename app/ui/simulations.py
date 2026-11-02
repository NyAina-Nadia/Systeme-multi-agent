import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSlider, QSpinBox,
                               QDoubleSpinBox, QLineEdit, QScrollArea, QFrame, QFormLayout, QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.db import engine
from app.ui.graphiques import InfoBulle
from app.theme import P, ACCENT, OR, SUCCES, styler_graphique
from app.ui.widgets import TitrePage, Carte, CarteKPI, etiquette
from ml.prevision import historique_mensuel_par_agence
from ml.simulations import (simuler_marge, simuler_agent, simuler_risque,
                            historique_mensuel_par_agent, objectifs_agents)

TOUTES = "Toutes les agences"


def _fmt(valeur):
    return f"{valeur:,.0f} M Ar".replace(",", " ")


def _vider(layout):
    while layout.count():
        it = layout.takeAt(0)
        if it.widget() is not None:
            it.widget().setParent(None)


def _slider(mini, maxi, suffixe=" %"):
    s = QSlider(Qt.Horizontal); s.setRange(mini, maxi); s.setValue(0); s.setMinimumWidth(260)
    l = QLabel("0 %"); l.setMinimumWidth(52)
    s.valueChanged.connect(lambda v, lab=l: lab.setText(f"{v:+d}{suffixe}"))
    return s, l


def _ligne(slider, label):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.addWidget(slider, 1); h.addWidget(label)
    return w


def _carte_graphique(titre):
    carte = Carte(); lay = QVBoxLayout(carte); lay.setContentsMargins(18, 14, 18, 14)
    lay.addWidget(etiquette(titre))
    graphique = pg.PlotWidget(); styler_graphique(graphique); graphique.setMinimumHeight(300)
    graphique.addLegend(offset=(10, 10))
    lay.addWidget(graphique)
    return carte, graphique


def _message(layout):
    msg = QLabel(""); msg.setObjectName("alerteNeutre"); msg.setWordWrap(True); msg.hide()
    layout.addWidget(msg)
    return msg


def _axe_horizon(graphique, n_hist, h):
    x = list(range(n_hist + h))
    graphique.getAxis("bottom").setTicks([[(i, f"M{i+1}" if i < n_hist else f"+{i-n_hist+1}") for i in x]])
    return x


class SimulationsScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self._bulles = {}

        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(16); layout.setContentsMargins(0, 0, 10, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        layout.addWidget(TitrePage("Simulations",
                                   "Marge, performance d'un agent et risque sur l'objectif : testez des hypothèses avant d'agir"))

        self.pivot = historique_mensuel_par_agence()
        self.objectifs = pd.read_sql("SELECT agence, COALESCE(objectif,0) AS objectif FROM dim_agence", engine) \
                           .set_index("agence")["objectif"].astype(float).to_dict()
        self.agences = list(self.objectifs.keys())

        self.onglets = QTabWidget()
        self.onglets.addTab(self._onglet_marge(), "Marge")
        self.onglets.addTab(self._onglet_agent(), "Performance d'un agent")
        self.onglets.addTab(self._onglet_risque(), "Risque")
        layout.addWidget(self.onglets)

        self.onglets.currentChanged.connect(lambda _: self.rafraichir_tout())
        self._agence_change()          # remplit la liste des agents puis lance toutes les simulations
        self.rafraichir_tout()

    # ------------------------------------------------------------------ utilitaires
    def _nettoyer_bulle(self, cle):
        if self._bulles.get(cle) is not None:
            self._bulles[cle].detacher(); self._bulles[cle] = None

    def _serie_perimetre(self, nom):
        if nom == TOUTES:
            return self.pivot.sum(axis=1).tolist(), sum(self.objectifs.get(a, 0) for a in self.pivot.columns) / 1e6
        return self.pivot[nom].tolist(), self.objectifs.get(nom, 0) / 1e6

    def _remplir_perimetres(self, combo):
        combo.addItem(TOUTES); combo.addItems(list(self.pivot.columns))

    def rafraichir_tout(self):
        for rafraichir in (self.rafraichir_marge, self.rafraichir_agent, self.rafraichir_risque):
            rafraichir()

    # ------------------------------------------------------------------ onglet Marge
    def _onglet_marge(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setSpacing(16); lay.setContentsMargins(0, 12, 0, 0)

        carte = Carte(); lp = QVBoxLayout(carte); lp.setContentsMargins(18, 14, 18, 14)
        lp.addWidget(etiquette("Paramètres de la simulation"))
        form = QFormLayout(); form.setHorizontalSpacing(18)
        self.m_perimetre = QComboBox(); self._remplir_perimetres(self.m_perimetre)
        self.m_taux = QDoubleSpinBox(); self.m_taux.setRange(0.1, 99.9); self.m_taux.setValue(20.0)
        self.m_taux.setSuffix(" %"); self.m_taux.setDecimals(1)
        self.m_prix, self.m_prix_l = _slider(-30, 30)
        self.m_volume, self.m_volume_l = _slider(-50, 50)
        self.m_horizon = QSpinBox(); self.m_horizon.setRange(1, 12); self.m_horizon.setValue(3); self.m_horizon.setSuffix(" mois")
        form.addRow("Périmètre", self.m_perimetre)
        form.addRow("Taux de marge actuel (marge ÷ CA)", self.m_taux)
        form.addRow("Variation des prix", _ligne(self.m_prix, self.m_prix_l))
        form.addRow("Variation des volumes", _ligne(self.m_volume, self.m_volume_l))
        form.addRow("Horizon", self.m_horizon)
        lp.addLayout(form)
        note = QLabel("Le taux de marge n'est pas enregistré dans la base : saisissez le taux moyen de votre activité. "
                      "Une baisse de prix ne change pas le coût unitaire ; une variation de volume ne change pas le taux de marge.")
        note.setObjectName("sousTitre"); note.setWordWrap(True); lp.addWidget(note)
        lay.addWidget(carte)

        self.m_kpi = QHBoxLayout(); self.m_kpi.setSpacing(16); lay.addLayout(self.m_kpi)
        self.m_carte_graph, self.m_graph = _carte_graphique("Marge cumulée sur l'horizon (M Ar) : actuelle et scénario")
        lay.addWidget(self.m_carte_graph)
        self.m_msg = _message(lay)

        self.m_perimetre.currentIndexChanged.connect(self.rafraichir_marge)
        self.m_taux.valueChanged.connect(self.rafraichir_marge)
        self.m_prix.valueChanged.connect(self.rafraichir_marge)
        self.m_volume.valueChanged.connect(self.rafraichir_marge)
        self.m_horizon.valueChanged.connect(self.rafraichir_marge)
        return page

    def rafraichir_marge(self, *_):
        if not hasattr(self, "m_graph"):
            return
        serie, _ = self._serie_perimetre(self.m_perimetre.currentText())
        self._nettoyer_bulle("marge")
        self.m_graph.clear(); _vider(self.m_kpi)
        if len(serie) < 3:
            self.m_msg.setText("Historique insuffisant (3 mois minimum)."); self.m_msg.show(); return
        self.m_msg.hide()
        h = self.m_horizon.value()
        r = simuler_marge(serie, self.m_taux.value(), self.m_prix.value(), self.m_volume.value(), h)

        x = list(range(h))
        base = [v for v in r["serie_marge_base"]]
        scen = [v for v in r["serie_marge_scenario"]]
        self.m_graph.plot(x, base, pen=pg.mkPen(P["serie1"], width=3), name="Marge actuelle")
        self.m_graph.plot(x, scen, pen=pg.mkPen(P["serie2"], width=3), name="Scénario")
        self.m_graph.getAxis("bottom").setTicks([[(i, f"+{i+1}") for i in x]])
        self._bulles["marge"] = InfoBulle(self.m_graph,
                                          [("Marge actuelle", x, base, P["serie1"]), ("Scénario", x, scen, P["serie2"])],
                                          {i: f"+{i+1}" for i in x}, fmt=_fmt)

        gain = r["gain_marge"]
        self.m_kpi.addWidget(CarteKPI("Marge du scénario", _fmt(r["marge_scenario_horizon"]),
                                      f"actuelle : {_fmt(r['marge_base_horizon'])}", P["serie2"], "🔮"))
        self.m_kpi.addWidget(CarteKPI("Gain de marge", f"{gain:+,.0f} M Ar".replace(",", " "),
                                      "sur l'horizon choisi", SUCCES if gain >= 0 else ACCENT, "💹"))
        self.m_kpi.addWidget(CarteKPI("Taux de marge du scénario", f"{r['taux_marge_scenario']:.1f} %",
                                      f"actuel : {r['taux_marge_actuel']:.1f} %", OR, "📊"))
        self.m_kpi.addWidget(CarteKPI("Baisse de prix limite", f"{r['prix_seuil_pct']:.0f} %",
                                      "au-delà, chaque vente fait perdre de l'argent", ACCENT, "⛔"))

    # ------------------------------------------------------------------ onglet Agent
    def _onglet_agent(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setSpacing(16); lay.setContentsMargins(0, 12, 0, 0)

        carte = Carte(); lp = QVBoxLayout(carte); lp.setContentsMargins(18, 14, 18, 14)
        lp.addWidget(etiquette("Paramètres de la simulation"))
        form = QFormLayout(); form.setHorizontalSpacing(18)
        self.a_agence = QComboBox(); self.a_agence.addItems(self.agences)
        self.a_agent = QComboBox(); self.a_agent.setMinimumWidth(200)
        self.a_variation, self.a_variation_l = _slider(-50, 100)
        self.a_horizon = QSpinBox(); self.a_horizon.setRange(1, 12); self.a_horizon.setValue(3); self.a_horizon.setSuffix(" mois")
        form.addRow("Agence", self.a_agence)
        form.addRow("Agent", self.a_agent)
        form.addRow("Variation de sa performance", _ligne(self.a_variation, self.a_variation_l))
        form.addRow("Horizon", self.a_horizon)
        lp.addLayout(form)
        note = QLabel("Simule la hausse ou la baisse du rythme mensuel d'un agent (moyenne de ses 3 derniers mois) "
                      "et son effet sur le total de son agence et sur son propre objectif.")
        note.setObjectName("sousTitre"); note.setWordWrap(True); lp.addWidget(note)
        lay.addWidget(carte)

        self.a_kpi = QHBoxLayout(); self.a_kpi.setSpacing(16); lay.addLayout(self.a_kpi)
        self.a_carte_graph, self.a_graph = _carte_graphique("CA cumulé de l'agence (M Ar) : trajectoire actuelle et scénario")
        lay.addWidget(self.a_carte_graph)
        self.a_msg = _message(lay)

        self.a_agence.currentIndexChanged.connect(self._agence_change)
        self.a_agent.currentIndexChanged.connect(self.rafraichir_agent)
        self.a_variation.valueChanged.connect(self.rafraichir_agent)
        self.a_horizon.valueChanged.connect(self.rafraichir_agent)
        return page

    def _agence_change(self, *_):
        self.a_agent.blockSignals(True)
        self.a_agent.clear()
        agence = self.a_agence.currentText()
        if agence:
            ventes = historique_mensuel_par_agent(agence)
            self.a_agent.addItems(sorted(ventes.keys()))
        self.a_agent.blockSignals(False)
        self.rafraichir_agent()

    def rafraichir_agent(self, *_):
        if not hasattr(self, "a_graph"):
            return
        self._nettoyer_bulle("agent")
        self.a_graph.clear(); _vider(self.a_kpi)
        agence, agent = self.a_agence.currentText(), self.a_agent.currentText()
        ventes = historique_mensuel_par_agent(agence) if agence else {}
        if not agent or len(ventes) == 0 or agent not in ventes or len(ventes[agent]) < 3:
            self.a_msg.setText("Historique insuffisant pour cet agent (3 mois minimum)."); self.a_msg.show(); return
        self.a_msg.hide()

        objectif_agence = self.objectifs.get(agence, 0) / 1e6
        objectif_agent = objectifs_agents(agence).get(agent, 0.0)
        h = self.a_horizon.value()
        r = simuler_agent(ventes, agent, self.a_variation.value(), objectif_agence, objectif_agent, h)

        n = r["n_historique"]
        x = list(range(n + h))
        self.a_graph.plot(x, r["serie_base"], pen=pg.mkPen(P["serie1"], width=3), name="Trajectoire actuelle")
        self.a_graph.plot(x, r["serie_scenario"], pen=pg.mkPen(P["serie2"], width=3), name="Scénario")
        if objectif_agence > 0:
            self.a_graph.addItem(pg.InfiniteLine(pos=objectif_agence, angle=0,
                                                 pen=pg.mkPen(P["serie3"], width=2, style=Qt.PenStyle.DashLine),
                                                 label="Objectif agence",
                                                 labelOpts={"color": P["serie3"], "position": 0.08}))
        etiq = {i: (f"M{i+1}" if i < n else f"+{i-n+1}") for i in x}
        _axe_horizon(self.a_graph, n, h)
        self._bulles["agent"] = InfoBulle(self.a_graph,
                                          [("Trajectoire actuelle", x, r["serie_base"], P["serie1"]),
                                           ("Scénario", x, r["serie_scenario"], P["serie2"])],
                                          etiq, fmt=_fmt)

        gain = r["gain_agence"]
        ts = r["taux_atteinte_agence_scenario"]
        self.a_kpi.addWidget(CarteKPI("Gain pour l'agence", f"{gain:+,.0f} M Ar".replace(",", " "),
                                      "sur l'horizon choisi", SUCCES if gain >= 0 else ACCENT, "💹"))
        self.a_kpi.addWidget(CarteKPI("Atteinte objectif agence",
                                      f"{ts:.0f} %" if ts is not None else "—",
                                      f"sans changement : {r['taux_atteinte_agence_base']:.0f} %" if ts is not None else "objectif non défini",
                                      SUCCES if (ts or 0) >= 100 else OR, "🎯"))
        tg = r["taux_atteinte_agent_scenario"]
        self.a_kpi.addWidget(CarteKPI("Atteinte objectif de l'agent",
                                      f"{tg:.0f} %" if tg is not None else "—",
                                      f"sans changement : {r['taux_atteinte_agent_base']:.0f} %" if tg is not None else "objectif non défini",
                                      SUCCES if (tg or 0) >= 100 else OR, "👤"))
        part = r["part_agent_pct"]
        self.a_kpi.addWidget(CarteKPI("Part de l'agent dans l'agence",
                                      f"{part:.0f} %" if part is not None else "—",
                                      "rythme des 3 derniers mois", ACCENT, "⛰"))

    # ------------------------------------------------------------------ onglet Risque
    def _onglet_risque(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setSpacing(16); lay.setContentsMargins(0, 12, 0, 0)

        carte = Carte(); lp = QVBoxLayout(carte); lp.setContentsMargins(18, 14, 18, 14)
        lp.addWidget(etiquette("Paramètres de la simulation"))
        form = QFormLayout(); form.setHorizontalSpacing(18)
        self.r_perimetre = QComboBox(); self._remplir_perimetres(self.r_perimetre)
        self.r_horizon = QSpinBox(); self.r_horizon.setRange(1, 12); self.r_horizon.setValue(3); self.r_horizon.setSuffix(" mois")
        self.r_objectif = QLineEdit(); self.r_objectif.setPlaceholderText("Objectif en M Ar")
        form.addRow("Périmètre", self.r_perimetre)
        form.addRow("Horizon", self.r_horizon)
        form.addRow("Objectif à atteindre (M Ar)", self.r_objectif)
        lp.addLayout(form)
        note = QLabel("10 000 tirages aléatoires à partir de la variabilité des 6 derniers mois. Les mois sont supposés "
                      "indépendants : la simulation n'intègre pas de tendance. C'est une fourchette probable, pas une prévision.")
        note.setObjectName("sousTitre"); note.setWordWrap(True); lp.addWidget(note)
        lay.addWidget(carte)

        self.r_kpi = QHBoxLayout(); self.r_kpi.setSpacing(16); lay.addLayout(self.r_kpi)
        self.r_carte_graph, self.r_graph = _carte_graphique(
            "CA cumulé (M Ar) : fourchette P10 – P90 autour de la médiane")
        lay.addWidget(self.r_carte_graph)
        self.r_msg = _message(lay)

        self.r_perimetre.currentIndexChanged.connect(self._perimetre_risque_change)
        self.r_objectif.editingFinished.connect(self.rafraichir_risque)
        self.r_horizon.valueChanged.connect(self.rafraichir_risque)
        self._perimetre_risque_change()
        return page

    def _perimetre_risque_change(self, *_):
        _, obj = self._serie_perimetre(self.r_perimetre.currentText())
        self.r_objectif.setText(f"{obj:.0f}")
        self.rafraichir_risque()

    def rafraichir_risque(self, *_):
        if not hasattr(self, "r_graph"):
            return
        serie, _ = self._serie_perimetre(self.r_perimetre.currentText())
        self._nettoyer_bulle("risque")
        self.r_graph.clear(); _vider(self.r_kpi)
        if len(serie) < 3:
            self.r_msg.setText("Historique insuffisant (3 mois minimum)."); self.r_msg.show(); return
        self.r_msg.hide()
        try:
            objectif = float(self.r_objectif.text().replace(" ", "") or 0)
        except ValueError:
            objectif = 0.0
        h = self.r_horizon.value()
        r = simuler_risque(serie, h, objectif)

        n = r["n_historique"]
        x = list(range(n + h))
        p10, mediane, p90 = r["serie_p10"], r["serie_mediane"], r["serie_p90"]

        couleur_bande = QColor(P["serie1"]); couleur_bande.setAlpha(60)
        courbe_basse = self.r_graph.plot(x, p10, pen=pg.mkPen(None))
        courbe_haute = self.r_graph.plot(x, p90, pen=pg.mkPen(None))
        self.r_graph.addItem(pg.FillBetweenItem(courbe_basse, courbe_haute, brush=pg.mkBrush(couleur_bande)))
        self.r_graph.plot(x, mediane, pen=pg.mkPen(P["serie1"], width=3), name="Médiane")
        if objectif > 0:
            self.r_graph.addItem(pg.InfiniteLine(pos=objectif, angle=0,
                                                 pen=pg.mkPen(P["serie3"], width=2, style=Qt.PenStyle.DashLine),
                                                 label="Objectif", labelOpts={"color": P["serie3"], "position": 0.08}))
        _axe_horizon(self.r_graph, n, h)
        etiq = {i: (f"M{i+1}" if i < n else f"+{i-n+1}") for i in x}
        self._bulles["risque"] = InfoBulle(self.r_graph,
                                           [("Médiane", x, mediane, P["serie1"]),
                                            ("Pessimiste (P10)", x, p10, P["serie2"]),
                                            ("Optimiste (P90)", x, p90, P["serie3"])],
                                           etiq, fmt=_fmt)

        proba = r["probabilite_objectif_pct"]
        self.r_kpi.addWidget(CarteKPI("CA cumulé probable (médiane)", _fmt(r["cumul_p50"]),
                                      f"fourchette 80 % : {_fmt(r['cumul_p10'])} à {_fmt(r['cumul_p90'])}",
                                      P["serie1"], "🎲"))
        self.r_kpi.addWidget(CarteKPI("Scénario pessimiste (P10)", _fmt(r["cumul_p10"]),
                                      "9 chances sur 10 de faire mieux", ACCENT, "🌧"))
        self.r_kpi.addWidget(CarteKPI("Scénario optimiste (P90)", _fmt(r["cumul_p90"]),
                                      "1 chance sur 10 de faire mieux", SUCCES, "☀️"))
        self.r_kpi.addWidget(CarteKPI("Probabilité d'atteindre l'objectif",
                                      f"{proba:.0f} %" if proba is not None else "—",
                                      "sur les tirages simulés" if proba is not None else "objectif non défini",
                                      SUCCES if (proba or 0) >= 50 else OR, "🎯"))
