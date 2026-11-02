import datetime as dt
import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
                               QTableWidget, QScrollArea, QFrame, QDateEdit)
from PySide6.QtCore import QDate, Qt
from app.db import engine
from app.theme import P, ACCENT, OR, SUCCES, styler_graphique
from app.calculs_dashboard import (etiquettes_mois, moyenne_mobile, variation_mensuelle, cumul, pic_creux,
                                   parts, tendance_pct_par_mois)
from app.ui.graphiques import (InfoBulle, LegendeInteractive, tracer_courbe, texte_valeur, couleur_alpha)
from app.ui.widgets import (Carte, CarteKPI, BandeauAccueil, etiquette, preparer_table, item,
                            fmt_ar, date_longue)
from ml.alertes import generer_alertes

PRESETS = ["Toute la période", "3 derniers mois", "6 derniers mois", "Dernier mois"]
MODES = ["Par agence", "Total et tendance", "Cumulé"]
PALETTE = ["#2A9D8F", "#E76F51", "#E9C46A", "#6C8EBF", "#8AB17D", "#B07CC6", "#F4A261", "#4D908E"]


def _qdate(d: dt.date) -> QDate:
    return QDate(d.year, d.month, d.day)


def _m(v: float) -> str:
    return f"{v:,.0f} M Ar".replace(",", " ")


def _graphique(hauteur=300):
    g = pg.PlotWidget()
    styler_graphique(g)
    g.setMenuEnabled(False)
    g.setMinimumHeight(hauteur)
    return g


class DashboardScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        self.d_min, self.d_max = self._bornes()
        self._bulle = None
        self._donnees = None                       # données mensuelles conservées pour changer de mode sans requête
        self._couleur_agence = {}

        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu)
        layout.setContentsMargins(0, 0, 10, 0); layout.setSpacing(16)
        defil.setWidget(contenu)
        externe = QVBoxLayout(self); externe.setContentsMargins(0, 0, 0, 0); externe.addWidget(defil)

        prenom = (utilisateur["nom"] or "").split(" ")[0] or "vous"
        self.bandeau = BandeauAccueil(
            f"Bonjour {prenom} 👋",
            "Vue d'ensemble de la performance commerciale",
            date_longue(),
            utilisateur.get("role", ""),
        )
        layout.addWidget(self.bandeau)

        # --- Filtres ---
        filtres = QHBoxLayout(); filtres.setSpacing(10)
        filtres.addStretch(1)
        self.filtre_agence = QComboBox(); self.filtre_agence.setMinimumWidth(180)
        self.filtre_agence.addItem("Toutes les agences", None)
        self.filtre_categorie = QComboBox(); self.filtre_categorie.setMinimumWidth(150)
        self.filtre_categorie.addItem("Toutes les catégories", None)
        self.combo_periode = QComboBox(); self.combo_periode.addItems(PRESETS)
        self.date_debut = QDateEdit(_qdate(self.d_min)); self.date_fin = QDateEdit(_qdate(self.d_max))
        for d in (self.date_debut, self.date_fin):
            d.setCalendarPopup(True); d.setDisplayFormat("dd/MM/yyyy")
        for lib, w in (("Agence", self.filtre_agence), ("Catégorie", self.filtre_categorie), ("Période", self.combo_periode),
                       ("Du", self.date_debut), ("au", self.date_fin)):
            l = QLabel(lib); l.setObjectName("sousTitre"); filtres.addWidget(l); filtres.addWidget(w)
        layout.addLayout(filtres)

        self.zone_kpi = QGridLayout(); self.zone_kpi.setSpacing(16)
        layout.addLayout(self.zone_kpi)
        self.zone_alertes = QVBoxLayout(); self.zone_alertes.setSpacing(8)
        layout.addLayout(self.zone_alertes)

        # --- Ligne 1 : évolution (large) + classement des agences ---
        ligne1 = QHBoxLayout(); ligne1.setSpacing(16)
        c1 = Carte(); l1 = QVBoxLayout(c1); l1.setContentsMargins(18, 14, 18, 14); l1.setSpacing(8)
        tete = QHBoxLayout()
        tete.addWidget(etiquette("Évolution du chiffre d'affaires (M Ar)"), 1)
        self.combo_mode = QComboBox(); self.combo_mode.addItems(MODES)
        tete.addWidget(self.combo_mode)
        l1.addLayout(tete)
        self.zone_legende = QHBoxLayout(); l1.addLayout(self.zone_legende)
        self.note_evol = QLabel(""); self.note_evol.setObjectName("sousTitre"); self.note_evol.setWordWrap(True)
        l1.addWidget(self.note_evol)
        self.g_evol = _graphique(320); l1.addWidget(self.g_evol)

        c2 = Carte(); l2 = QVBoxLayout(c2); l2.setContentsMargins(18, 14, 18, 14); l2.setSpacing(8)
        l2.addWidget(etiquette("CA par agence et objectif (M Ar)"))
        note2 = QLabel("Barre : CA réalisé · trait gris : objectif de l'agence"); note2.setObjectName("sousTitre")
        l2.addWidget(note2)
        self.g_rang = _graphique(320); l2.addWidget(self.g_rang)
        ligne1.addWidget(c1, 3); ligne1.addWidget(c2, 2)
        layout.addLayout(ligne1)

        # --- Ligne 2 : variation mensuelle + répartition par catégorie ---
        ligne2 = QHBoxLayout(); ligne2.setSpacing(16)
        c3 = Carte(); l3 = QVBoxLayout(c3); l3.setContentsMargins(18, 14, 18, 14); l3.setSpacing(8)
        l3.addWidget(etiquette("Variation mensuelle du CA (%)"))
        self.g_var = _graphique(250); l3.addWidget(self.g_var)
        c4 = Carte(); l4 = QVBoxLayout(c4); l4.setContentsMargins(18, 14, 18, 14); l4.setSpacing(8)
        l4.addWidget(etiquette("Répartition du CA par catégorie"))
        self.g_cat = _graphique(250); l4.addWidget(self.g_cat)
        ligne2.addWidget(c3, 1); ligne2.addWidget(c4, 1)
        layout.addLayout(ligne2)

        # --- Top produits ---
        c5 = Carte(); l5 = QVBoxLayout(c5); l5.setContentsMargins(18, 14, 18, 14)
        l5.addWidget(etiquette("Top 5 des produits"))
        self.table_top = QTableWidget(); preparer_table(self.table_top)
        self.table_top.setColumnCount(3)
        self.table_top.setHorizontalHeaderLabels(["Produit", "Quantités vendues", "Chiffre d'affaires"])
        self.table_top.setMinimumHeight(250)
        l5.addWidget(self.table_top)
        layout.addWidget(c5)

        if utilisateur["role"] == "agent" and utilisateur["id_agence"]:
            self.filtre_agence.setEnabled(False)
        self.charger_liste_agences()
        self.charger_categories()

        self.filtre_agence.currentIndexChanged.connect(self.rafraichir)
        self.filtre_categorie.currentIndexChanged.connect(self.rafraichir)
        self.combo_periode.currentIndexChanged.connect(self.appliquer_preset)
        self.date_debut.dateChanged.connect(self.rafraichir)
        self.date_fin.dateChanged.connect(self.rafraichir)
        self.combo_mode.currentIndexChanged.connect(self.dessiner_evolution)
        self.rafraichir()

    # ------------------------------------------------------------------ filtres
    def _bornes(self):
        try:
            r = pd.read_sql("SELECT MIN(date) AS a, MAX(date) AS b FROM dim_date", engine).iloc[0]
            if pd.notna(r["a"]) and pd.notna(r["b"]):
                return pd.to_datetime(r["a"]).date(), pd.to_datetime(r["b"]).date()
        except Exception:
            pass
        return dt.date.today() - dt.timedelta(days=365), dt.date.today()

    def appliquer_preset(self):
        choix = self.combo_periode.currentText()
        fin = pd.Timestamp(self.d_max)
        if choix == "3 derniers mois":
            debut = fin - pd.DateOffset(months=3) + pd.Timedelta(days=1)
        elif choix == "6 derniers mois":
            debut = fin - pd.DateOffset(months=6) + pd.Timedelta(days=1)
        elif choix == "Dernier mois":
            debut = fin.replace(day=1)
        else:
            debut = pd.Timestamp(self.d_min)
        debut = max(debut.date(), self.d_min)
        for w, d in ((self.date_debut, debut), (self.date_fin, fin.date())):
            w.blockSignals(True); w.setDate(_qdate(d)); w.blockSignals(False)
        self.rafraichir()

    def _periode(self):
        return self.date_debut.date().toPython(), self.date_fin.date().toPython()

    def _id_agence(self):
        if self.utilisateur["role"] == "agent" and self.utilisateur["id_agence"]:
            return self.utilisateur["id_agence"]
        return self.filtre_agence.currentData()

    def clause(self, d1, d2):
        conds = ["dd.date BETWEEN %(d1)s AND %(d2)s"]
        params = {"d1": d1, "d2": d2}
        a = self._id_agence()
        if a:
            conds.append("f.id_agence = %(id_agence)s"); params["id_agence"] = int(a)
        cat = self.filtre_categorie.currentData()
        if cat:
            conds.append("dp.categorie = %(categorie)s"); params["categorie"] = cat
        return "WHERE " + " AND ".join(conds), params

    def charger_categories(self):
        try:
            df = pd.read_sql("SELECT DISTINCT categorie FROM dim_produit WHERE categorie IS NOT NULL ORDER BY categorie", engine)
            for c in df["categorie"]:
                self.filtre_categorie.addItem(str(c), str(c))
        except Exception:
            pass

    def charger_liste_agences(self):
        df = pd.read_sql("SELECT id_agence, agence FROM dim_agence ORDER BY agence", engine)
        for i, (_, row) in enumerate(df.iterrows()):
            self.filtre_agence.addItem(row["agence"], int(row["id_agence"]))
            self._couleur_agence[row["agence"]] = PALETTE[i % len(PALETTE)]      # couleur stable d'une agence à l'autre
        if self.utilisateur["role"] == "agent" and self.utilisateur["id_agence"]:
            i = self.filtre_agence.findData(self.utilisateur["id_agence"])
            if i >= 0:
                self.filtre_agence.setCurrentIndex(i)

    def _vider(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide(); w.setParent(None); w.deleteLater()
            elif it.layout() is not None:
                self._vider(it.layout())

    def _totaux(self, d1, d2):
        clause, params = self.clause(d1, d2)
        r = pd.read_sql(f"""SELECT COALESCE(SUM(f.montant),0) AS ca, COUNT(*) AS nb
            FROM fait_vente f JOIN dim_date dd ON dd.id_temps = f.id_temps
            JOIN dim_produit dp ON dp.id_produit = f.id_produit {clause}""",
                        engine, params=params).iloc[0]
        return float(r["ca"]), int(r["nb"])

    @staticmethod
    def _delta(actuel, precedent):
        return (actuel / precedent - 1) * 100 if precedent else None

    # ------------------------------------------------------------------ données
    def rafraichir(self, *_):
        d1, d2 = self._periode()
        if d1 > d2:
            return
        clause, params = self.clause(d1, d2)

        df = pd.read_sql(f"""
            SELECT da.agence, COALESCE(da.objectif, 0) AS objectif, SUM(f.montant) AS ca, COUNT(*) AS nb_ventes
            FROM fait_vente f JOIN dim_agence da ON da.id_agence = f.id_agence
            JOIN dim_date dd ON dd.id_temps = f.id_temps
            JOIN dim_produit dp ON dp.id_produit = f.id_produit
            {clause} GROUP BY da.agence, da.objectif ORDER BY ca DESC""", engine, params=params)
        mens = pd.read_sql(f"""
            SELECT dd.annee, dd.mois, da.agence, SUM(f.montant) AS ca, COUNT(*) AS nb
            FROM fait_vente f JOIN dim_date dd ON dd.id_temps = f.id_temps
            JOIN dim_agence da ON da.id_agence = f.id_agence
            JOIN dim_produit dp ON dp.id_produit = f.id_produit
            {clause} GROUP BY dd.annee, dd.mois, da.agence ORDER BY dd.annee, dd.mois""", engine, params=params)
        cats = pd.read_sql(f"""
            SELECT dp.categorie, SUM(f.montant) AS ca
            FROM fait_vente f JOIN dim_date dd ON dd.id_temps = f.id_temps
            JOIN dim_produit dp ON dp.id_produit = f.id_produit
            {clause} GROUP BY dp.categorie ORDER BY ca DESC""", engine, params=params)
        top = pd.read_sql(f"""
            SELECT dp.produit, SUM(f.quantite) AS qte, SUM(f.montant) AS ca
            FROM fait_vente f JOIN dim_produit dp ON dp.id_produit = f.id_produit
            JOIN dim_date dd ON dd.id_temps = f.id_temps
            {clause} GROUP BY dp.produit ORDER BY ca DESC LIMIT 5""", engine, params=params)

        # ---- Période précédente de même durée (variations) ----
        duree = (d2 - d1).days + 1
        p2 = d1 - dt.timedelta(days=1)
        p1 = p2 - dt.timedelta(days=duree - 1)
        ca_prec, nb_prec = self._totaux(p1, p2)

        self.bandeau.lbl_sous.setText(
            f"{date_longue()}  ·  Période du {d1:%d/%m/%Y} au {d2:%d/%m/%Y}  ·  {len(df)} agence(s) affichée(s)")

        # ---- Séries mensuelles alignées (une ligne par mois, une colonne par agence) ----
        if mens.empty:
            self._donnees = None
            periodes, totaux, nbs, par_agence = [], np.array([]), np.array([]), {}
        else:
            mens["ca"] = mens["ca"].astype(float)
            periodes = sorted({(int(a), int(m)) for a, m in zip(mens["annee"], mens["mois"])})
            pos = {p: i for i, p in enumerate(periodes)}
            par_agence = {}
            nbs = np.zeros(len(periodes))
            for _, r in mens.iterrows():
                i = pos[(int(r["annee"]), int(r["mois"]))]
                par_agence.setdefault(r["agence"], np.zeros(len(periodes)))[i] += r["ca"] / 1e6
                nbs[i] += r["nb"]
            totaux = np.sum(list(par_agence.values()), axis=0)
            self._donnees = {"periodes": periodes, "par_agence": par_agence, "totaux": totaux,
                             "objectif": float(df["objectif"].sum()) / 1e6 if not df.empty else 0.0}

        # ---- KPI ----
        self._vider(self.zone_kpi)
        ca_total = float(df["ca"].sum()) if not df.empty else 0.0
        nb = int(df["nb_ventes"].sum()) if not df.empty else 0
        panier = ca_total / nb if nb else 0.0
        panier_prec = ca_prec / nb_prec if nb_prec else 0.0
        meilleure = df.iloc[0]["agence"] if not df.empty else "—"
        s_ca = totaux.tolist() if len(totaux) >= 2 else None
        s_nb = nbs.tolist() if len(nbs) >= 2 else None
        s_pm = np.nan_to_num(totaux * 1e6 / np.where(nbs == 0, np.nan, nbs)).tolist() if len(totaux) >= 2 else None
        tendance = tendance_pct_par_mois(totaux) if len(totaux) else None
        sous_ca = "vs période précédente" if tendance is None else f"tendance {tendance:+.1f} %/mois"
        cartes = [
            CarteKPI("Chiffre d'affaires", _m(ca_total / 1e6), sous_ca, P["serie1"], "💰",
                     self._delta(ca_total, ca_prec), s_ca),
            CarteKPI("Panier moyen", fmt_ar(panier, millions=False), "vs période précédente", OR, "🧺",
                     self._delta(panier, panier_prec), s_pm),
            CarteKPI("Nombre de ventes", f"{nb:,}".replace(",", " "), "vs période précédente", ACCENT, "🧾",
                     self._delta(nb, nb_prec), s_nb),
            CarteKPI("Agence en tête", str(meilleure), f"{len(df)} agence(s)", SUCCES, "🏆"),
        ]
        for i, c in enumerate(cartes):
            self.zone_kpi.addWidget(c, 0, i)

        # ---- Graphiques ----
        self.dessiner_evolution()
        self.dessiner_classement(df)
        self.dessiner_variation(periodes, totaux)
        self.dessiner_categories(cats)

        # ---- Alertes (hors rôle agent) ----
        self._vider(self.zone_alertes)
        if self.utilisateur["role"] != "agent":
            alertes = generer_alertes()
            if not alertes:
                lbl = QLabel("✓  Aucune alerte détectée."); lbl.setObjectName("alerteNeutre")
                self.zone_alertes.addWidget(lbl)
            for a in alertes:
                icone, nom = ("⚠", "alerteRisque") if a["niveau"] == "risque" else ("▲", "alertePositif")
                lbl = QLabel(f"{icone}   {a['texte']}"); lbl.setObjectName(nom); lbl.setWordWrap(True)
                self.zone_alertes.addWidget(lbl)

        # ---- Top produits ----
        self.table_top.setRowCount(len(top))
        for i, (_, r) in enumerate(top.iterrows()):
            self.table_top.setItem(i, 0, item(r["produit"]))
            self.table_top.setItem(i, 1, item(f"{int(r['qte']):,}".replace(",", " "), True))
            self.table_top.setItem(i, 2, item(fmt_ar(float(r["ca"])), True))
        self.table_top.resizeColumnsToContents()

    # ------------------------------------------------------------------ graphiques
    def dessiner_evolution(self, *_):
        if self._bulle is not None:
            self._bulle.detacher(); self._bulle = None
        g = self.g_evol
        g.clear()
        self._vider(self.zone_legende)
        self.note_evol.setText("")
        d = self._donnees
        if not d or len(d["totaux"]) == 0:
            self.note_evol.setText("Aucune vente sur cette sélection.")
            return
        periodes, totaux = d["periodes"], d["totaux"]
        n = len(periodes)
        x = list(range(n))
        libelles = etiquettes_mois(periodes)
        etiq = dict(enumerate(libelles))
        mode = self.combo_mode.currentText()
        entrees, series = [], []

        if mode == "Par agence":
            for nom, y in d["par_agence"].items():
                c = self._couleur_agence.get(nom, PALETTE[len(entrees) % len(PALETTE)])
                els = tracer_courbe(g, x, y, c, aire=len(d["par_agence"]) == 1)
                entrees.append((nom, c, els)); series.append((nom, x, y, c))
            ymax = max(float(np.max(y)) for y in d["par_agence"].values())
            self.note_evol.setText("Cliquez sur une agence pour la masquer ou l'afficher.")
        elif mode == "Total et tendance":
            c1, c2 = P["serie1"], P["serie2"]
            els = tracer_courbe(g, x, totaux, c1, aire=True)
            entrees.append(("Total", c1, els)); series.append(("Total", x, totaux, c1))
            mm = moyenne_mobile(totaux, 3)
            valides = [i for i in x if not np.isnan(mm[i])]
            if len(valides) >= 2:
                els2 = tracer_courbe(g, valides, [mm[i] for i in valides], c2, lisse=False, points=False, pointille=True, largeur=3)
                entrees.append(("Moyenne mobile 3 mois", c2, els2))
                series.append(("Moyenne mobile 3 mois", valides, [mm[i] for i in valides], c2))
            ip, ic = pic_creux(totaux)
            if ip is not None:
                texte_valeur(g, ip, totaux[ip], f"▲ Pic : {_m(totaux[ip])}", (0.5, 1.2), SUCCES)
                if ic != ip:
                    texte_valeur(g, ic, totaux[ic], f"▼ Creux : {_m(totaux[ic])}", (0.5, -0.2), ACCENT)
            ymax = float(np.max(totaux))
            t = tendance_pct_par_mois(totaux)
            if t is not None:
                self.note_evol.setText(f"Tendance linéaire : {t:+.1f} % de la moyenne par mois.")
        else:  # Cumulé
            c1 = P["serie1"]
            cum = cumul(totaux)
            els = tracer_courbe(g, x, cum, c1, aire=True)
            entrees.append(("CA cumulé", c1, els)); series.append(("CA cumulé", x, cum, c1))
            ymax = float(cum[-1])
            if d["objectif"] > 0:
                ligne = pg.InfiniteLine(pos=d["objectif"], angle=0, pen=pg.mkPen(P["serie3"], width=2, style=Qt.DashLine),
                                        label=f"Objectif : {_m(d['objectif'])}",
                                        labelOpts={"color": P["serie3"], "position": 0.12})
                g.addItem(ligne)
                entrees.append(("Objectif", P["serie3"], [ligne]))
                ymax = max(ymax, d["objectif"])
                self.note_evol.setText(f"Réalisé : {cum[-1] / d['objectif'] * 100:.0f} % de l'objectif cumulé des agences affichées.")

        g.getAxis("bottom").setTicks([list(zip(x, libelles))])
        g.setYRange(0, max(ymax, 1.0) * 1.18, padding=0)
        g.setXRange(-0.4, max(n - 0.6, 0.6), padding=0)
        self.zone_legende.addWidget(LegendeInteractive(entrees))
        self._bulle = InfoBulle(g, series, etiq, fmt=_m)

    def dessiner_classement(self, df):
        g = self.g_rang
        g.clear()
        if df.empty:
            return
        df = df.sort_values("ca", ascending=False).reset_index(drop=True)
        ca = df["ca"].astype(float).to_numpy() / 1e6
        obj = df["objectif"].astype(float).to_numpy() / 1e6
        y = np.arange(len(df), dtype=float)
        brosses = [pg.mkBrush(self._couleur_agence.get(a, PALETTE[i % len(PALETTE)])) for i, a in enumerate(df["agence"])]
        g.addItem(pg.BarGraphItem(x0=np.zeros(len(df)), x1=ca, y=y, height=0.56, brushes=brosses, pen=pg.mkPen(None)))
        xmax = float(max(ca.max(), obj.max() if len(obj) else 0))
        for i in range(len(df)):
            if obj[i] > 0:
                g.addItem(pg.PlotCurveItem([obj[i], obj[i]], [i - 0.4, i + 0.4], pen=pg.mkPen(P["doux"], width=3)))
            taux = f" · {ca[i] / obj[i] * 100:.0f} %" if obj[i] > 0 else ""
            texte_valeur(g, max(ca[i], obj[i]) + xmax * 0.02, i, f"{ca[i]:,.0f} M{taux}".replace(",", " "), (0, 0.5))
        g.getAxis("left").setTicks([[(i, a) for i, a in enumerate(df["agence"])]])
        g.getAxis("left").setWidth(100)
        g.invertY(True)
        g.showGrid(x=True, y=False, alpha=0.15)
        g.setXRange(0, xmax * 1.5, padding=0)
        g.setYRange(-0.6, len(df) - 0.4, padding=0)

    def dessiner_variation(self, periodes, totaux):
        g = self.g_var
        g.clear()
        v = variation_mensuelle(totaux)
        if len(v) == 0:
            return
        libelles = etiquettes_mois(periodes)[1:]
        x = np.arange(len(v), dtype=float)
        valeurs = np.nan_to_num(v, nan=0.0)
        brosses = [pg.mkBrush(SUCCES if val >= 0 else ACCENT) for val in valeurs]
        g.addItem(pg.BarGraphItem(x=x, height=valeurs, width=0.62, brushes=brosses, pen=pg.mkPen(None)))
        g.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(P["doux"], width=1)))
        amp = max(float(np.max(np.abs(valeurs))), 1.0)
        for i, val in enumerate(v):
            if not np.isnan(val):
                texte_valeur(g, i, val, f"{val:+.0f} %", (0.5, 1.15) if val >= 0 else (0.5, -0.15),
                             SUCCES if val >= 0 else ACCENT)
        g.getAxis("bottom").setTicks([list(zip(x, libelles))])
        g.setYRange(-amp * 1.35, amp * 1.35, padding=0)
        g.setXRange(-0.6, len(v) - 0.4, padding=0)

    def dessiner_categories(self, cats):
        g = self.g_cat
        g.clear()
        if cats.empty:
            return
        repartition = parts({str(c): float(v) for c, v in zip(cats["categorie"], cats["ca"])}, top=7)
        n = len(repartition)
        y = np.arange(n, dtype=float)
        valeurs = np.array([r[1] for r in repartition]) / 1e6
        brosses = [pg.mkBrush(PALETTE[i % len(PALETTE)]) for i in range(n)]
        g.addItem(pg.BarGraphItem(x0=np.zeros(n), x1=valeurs, y=y, height=0.56, brushes=brosses, pen=pg.mkPen(None)))
        xmax = float(valeurs.max())
        for i, (nom, v, pct) in enumerate(repartition):
            texte_valeur(g, valeurs[i] + xmax * 0.02, i, f"{pct:.0f} % · {v / 1e6:,.0f} M".replace(",", " "), (0, 0.5))
        g.getAxis("left").setTicks([[(i, r[0]) for i, r in enumerate(repartition)]])
        g.getAxis("left").setWidth(110)
        g.invertY(True)
        g.showGrid(x=True, y=False, alpha=0.15)
        g.setXRange(0, xmax * 1.6, padding=0)
        g.setYRange(-0.6, n - 0.4, padding=0)
