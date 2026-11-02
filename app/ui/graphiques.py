"""Composants graphiques communs (pyqtgraph) : courbes lissées, bulle au survol, légende interactive."""
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from app.theme import P

try:
    from scipy.interpolate import PchipInterpolator      # installé avec scikit-learn
except Exception:                                         # repli : courbe en segments droits
    PchipInterpolator = None


def couleur_alpha(couleur, alpha):
    c = QColor(couleur)
    c.setAlpha(alpha)
    return c


def lisser(x, y, pas=10):
    """Courbe lissée par interpolation monotone (PCHIP) : pas de dépassement entre deux points réels."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if PchipInterpolator is None or len(x) < 3:
        return x, y
    xs = np.linspace(x.min(), x.max(), (len(x) - 1) * pas + 1)
    return xs, PchipInterpolator(x, y)(xs)


def tracer_courbe(plot, x, y, couleur, aire=False, lisse=True, largeur=3, points=True, pointille=False):
    """Ajoute une courbe (lissée) et ses points réels. Retourne la liste des éléments (pour la légende)."""
    xs, ys = lisser(x, y) if lisse else (np.asarray(x, float), np.asarray(y, float))
    pen = pg.mkPen(couleur, width=largeur, style=Qt.DashLine if pointille else Qt.SolidLine)
    options = {"pen": pen}
    if aire:
        options.update(fillLevel=0, brush=couleur_alpha(couleur, 45))
    courbe = pg.PlotCurveItem(xs, ys, **options)
    plot.addItem(courbe)
    elements = [courbe]
    if points:
        pts = pg.ScatterPlotItem(x=[float(v) for v in x], y=[float(v) for v in y], size=8,
                                 brush=pg.mkBrush(couleur), pen=pg.mkPen(P["carte"], width=1.5))
        plot.addItem(pts)
        elements.append(pts)
    return elements


def texte_valeur(plot, x, y, texte, ancre=(0.5, 1), couleur=None):
    """Petite étiquette de valeur posée sur le graphique."""
    t = pg.TextItem(texte, color=couleur or P["texte"], anchor=ancre)
    t.setPos(float(x), float(y))
    plot.addItem(t)
    return t


class InfoBulle:
    """Réticule vertical + bulle d'informations au survol du graphique.
    series : liste de (nom, x[], y[], couleur) ; etiquettes : {x: texte de l'axe} ;
    extra(x) -> ligne HTML facultative ; fmt(valeur) -> texte."""

    def __init__(self, plot, series, etiquettes=None, fmt=None, extra=None):
        self.plot = plot
        self.etiq = etiquettes or {}
        self.fmt = fmt or (lambda v: f"{v:,.1f}".replace(",", " "))
        self.extra = extra
        self.series = []
        for nom, x, y, couleur in series:
            d = {float(a): float(b) for a, b in zip(x, y) if b == b}        # b == b : écarte les NaN
            if d:
                self.series.append((nom, d, couleur))
        self.xs = sorted({a for _, d, _ in self.series for a in d})
        self.ligne = pg.InfiniteLine(angle=90, movable=False,
                                     pen=pg.mkPen(P["doux"], width=1, style=Qt.DashLine))
        self.texte = pg.TextItem(color=P["texte"], border=pg.mkPen(P["bordure"]), fill=pg.mkBrush(P["carte"]),
                                 anchor=(0, 0))
        self.ligne.setZValue(50)
        self.texte.setZValue(60)
        plot.addItem(self.ligne, ignoreBounds=True)
        plot.addItem(self.texte, ignoreBounds=True)
        self.ligne.hide()
        self.texte.hide()
        self._proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=30, slot=self._bouger)

    def detacher(self):
        """À appeler AVANT plot.clear() quand le graphique est redessiné."""
        try:
            self._proxy.disconnect()
        except Exception:
            pass
        for element in (self.ligne, self.texte):
            try:
                self.plot.removeItem(element)
            except Exception:
                pass

    def _ancrer(self, droite):
        a = (1, 0) if droite else (0, 0)
        try:
            self.texte.setAnchor(a)
        except Exception:
            self.texte.anchor = pg.Point(*a)

    def _bouger(self, evt):
        try:
            pos = evt[0]
            if not self.xs or not self.plot.sceneBoundingRect().contains(pos):
                self.ligne.hide(); self.texte.hide()
                return
            vb = self.plot.getPlotItem().vb
            x = vb.mapSceneToView(pos).x()
            xp = min(self.xs, key=lambda v: abs(v - x))
            lignes = [f"<span style='color:{c}'>●</span> {n} : <b>{self.fmt(d[xp])}</b>"
                      for n, d, c in self.series if xp in d]
            if not lignes:
                self.ligne.hide(); self.texte.hide()
                return
            titre = self.etiq.get(xp, self.etiq.get(int(xp), ""))
            extra = self.extra(xp) if self.extra else ""
            html = (f"<div style='padding:3px;font-size:12px'><b>{titre}</b><br>" + "<br>".join(lignes)
                    + (f"<br>{extra}" if extra else "") + "</div>")
            self.texte.setHtml(html)
            (x0, x1), (y0, y1) = vb.viewRange()
            self._ancrer(xp > (x0 + x1) / 2)
            self.texte.setPos(xp, y1)
            self.ligne.setPos(xp)
            self.ligne.show(); self.texte.show()
        except Exception:
            pass          # une infobulle ne doit jamais faire planter l'écran


class LegendeInteractive(QWidget):
    """Légende cliquable : un clic masque ou affiche la série correspondante.
    entrees : liste de (nom, couleur, [éléments pyqtgraph])."""

    def __init__(self, entrees, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        for nom, couleur, elements in entrees:
            b = QPushButton(f"●  {nom}")
            b.setCheckable(True)
            b.setChecked(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self._style(couleur, True))
            b.toggled.connect(lambda actif, b=b, c=couleur, els=elements: self._basculer(b, c, els, actif))
            lay.addWidget(b)
        lay.addStretch(1)

    @staticmethod
    def _style(couleur, actif):
        c = couleur if actif else P["doux"]
        bord = couleur if actif else P["bordure"]
        return (f"QPushButton {{ background: transparent; color: {c}; border: 1px solid {bord}; "
                f"border-radius: 12px; padding: 3px 11px; font-weight: 700; font-size: 11px; }}")

    def _basculer(self, bouton, couleur, elements, actif):
        for e in elements:
            e.setVisible(actif)
        bouton.setStyleSheet(self._style(couleur, actif))
