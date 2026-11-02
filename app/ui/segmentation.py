import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QScrollArea, QFrame
from ml.segmentation import segmenter_agents
from app.theme import styler_graphique, SUCCES, OR, ACCENT
from app.ui.widgets import TitrePage, Carte, etiquette, preparer_table, item, fmt_ar, badge

COULEURS = {"Performants": SUCCES, "Réguliers": OR, "À accompagner": ACCENT}
BADGE = {"Performants": "vert", "Réguliers": "ambre", "À accompagner": "rouge"}


class SegmentationScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(14); layout.setContentsMargins(0, 0, 10, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        layout.addWidget(TitrePage("Segmentation",
                                   "K-means sur 6 variables : CA, ventes, panier, clients, produits et régularité mensuelle"))
        carte = Carte(); lc = QVBoxLayout(carte); lc.setContentsMargins(18, 14, 18, 14)
        lc.addWidget(etiquette("CA (M Ar) en fonction du nombre de ventes, par segment"))
        self.graphique = pg.PlotWidget(); styler_graphique(self.graphique)
        self.graphique.addLegend(offset=(10, 10)); self.graphique.setMinimumHeight(300)
        self.graphique.setLabel("bottom", "Nombre de ventes"); self.graphique.setLabel("left", "CA (M Ar)")
        lc.addWidget(self.graphique)
        layout.addWidget(carte)

        carte2 = Carte(); l2 = QVBoxLayout(carte2); l2.setContentsMargins(18, 14, 18, 14)
        l2.addWidget(etiquette("Détail par agent (un agent est identifié par son nom ET son agence)"))
        self.table = QTableWidget(); preparer_table(self.table); self.table.setMinimumHeight(340)
        l2.addWidget(self.table)
        layout.addWidget(carte2)
        self.rafraichir()

    def rafraichir(self, *_):
        df = segmenter_agents()
        self.graphique.clear()
        if df.empty or "segment" not in df:
            return
        for segment, couleur in COULEURS.items():
            sous = df[df["segment"] == segment]
            if sous.empty:
                continue
            self.graphique.plot(sous["n"].tolist(), (sous["ca"] / 1e6).tolist(), pen=None, symbol="o",
                                symbolBrush=couleur, symbolSize=11, name=f"{segment} ({len(sous)})")
        colonnes = ["Agent", "Segment", "CA", "Ventes", "Panier moyen", "Clients", "Produits", "Irrégularité"]
        self.table.setColumnCount(len(colonnes)); self.table.setHorizontalHeaderLabels(colonnes)
        ordre = {"Performants": 0, "Réguliers": 1, "À accompagner": 2}
        df = df.assign(_o=df["segment"].map(ordre)).sort_values(["_o", "ca"], ascending=[True, False])
        self.table.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            self.table.setItem(i, 0, item(r["agent"]))
            self.table.setCellWidget(i, 1, badge(r["segment"], BADGE[r["segment"]]))
            self.table.setItem(i, 2, item(fmt_ar(r["ca"]), True))
            self.table.setItem(i, 3, item(int(r["n"]), True))
            self.table.setItem(i, 4, item(fmt_ar(r["panier"], False), True))
            self.table.setItem(i, 5, item(int(r["clients"]), True))
            self.table.setItem(i, 6, item(int(r["produits"]), True))
            self.table.setItem(i, 7, item(f"{r['irregularite']:.2f}", True))
        self.table.resizeColumnsToContents()
