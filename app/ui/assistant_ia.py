import os
import requests
import pandas as pd
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel
)

from app.db import engine
from ml.prevision import prevoir
from ml.anomalies import detecter_anomalies
from app.ui.widgets import TitrePage


# ---------------------------------------------------------------------
# OLLAMA
# ---------------------------------------------------------------------

API_URL = os.environ.get(
    "LLM_API_URL",
    "http://localhost:11434/api/chat"
)

MODEL = os.environ.get(
    "LLM_MODEL",
    "llama3.2"
)


def construire_contexte(id_agence=None) -> str:
    """id_agence : restreint le contexte à une agence (rôle agent)."""
    filtre = "WHERE da.id_agence = %(i)s" if id_agence else ""
    params = {"i": int(id_agence)} if id_agence else None

    kpi = pd.read_sql("""
        SELECT da.agence, da.objectif, COALESCE(SUM(f.montant),0) AS ca
        FROM dim_agence da
        LEFT JOIN fait_vente f ON f.id_agence = da.id_agence
        {filtre}
        GROUP BY da.agence, da.objectif
        ORDER BY ca DESC
    """.replace("{filtre}", filtre), engine, params=params)

    lignes = [
        "Résultats déjà calculés par le système (à utiliser tels quels, "
        "ne recalculer aucun chiffre) :",
        ""
    ]

    for _, r in kpi.iterrows():

        ecart = (
            (r["ca"] - r["objectif"]) / r["objectif"] * 100
            if r["objectif"]
            else 0
        )

        lignes.append(
            f"- {r['agence']} : CA = {r['ca']/1e6:.0f} M Ar, "
            f"objectif = {r['objectif']/1e6:.0f} M Ar, "
            f"écart = {ecart:+.0f} %"
        )

    # Explication des modèles de prévision (modèle retenu, erreur, dérive)
    try:
        from ml.backtest import diagnostic
        from ml.prevision import historique_mensuel_par_agence
        from ml.series import serie_agence
        piv = historique_mensuel_par_agence()
        modeles = []
        for agence in kpi["agence"]:
            _, y = serie_agence(piv, agence)
            if len(y) >= 7:
                d = diagnostic(y)
                ligne = d["tableau"][d["tableau"]["modele"] == d["retenu"]].iloc[0]
                modeles.append(f"- {agence} : modèle retenu = {d['retenu']} (erreur moyenne {ligne['mape']:.0f} % en backtest). "
                               f"{d['recommandation']}")
        if modeles:
            lignes.append("\nPrévisions (modèles et fiabilité) :")
            lignes.extend(modeles)
    except Exception:
        pass

    anomalies = detecter_anomalies(top_n=50)
    anomalies = anomalies[anomalies["agence"].isin(kpi["agence"])].head(3)

    if not anomalies.empty:

        lignes.append("\nAnomalies détectées récemment :")

        for _, a in anomalies.iterrows():

            lignes.append(
                f"- {a['agence']} : {a['produit']}, "
                f"{a['montant']:,.0f} Ar "
                f"({a['ratio']:.1f}× la médiane de l'agence) — niveau {a['niveau']} : {a['motifs']}"
            )

    return "\n".join(lignes)


def interroger_assistant(question: str, id_agence=None) -> str:

    contexte = construire_contexte(id_agence)

    try:

        reponse = requests.post(
            API_URL,

            json={
                "model": MODEL,

                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es un assistant spécialisé en Business Intelligence. "
                            "Tu expliques uniquement les résultats déjà calculés "
                            "par le système décisionnel. "
                            "Tu ne dois jamais recalculer, estimer ou inventer "
                            "un chiffre qui n'apparaît pas explicitement "
                            "dans le contexte fourni. "
                            "Si une information n'est pas présente dans le contexte, "
                            "dis clairement qu'elle n'est pas disponible."
                        )
                    },

                    {
                        "role": "system",
                        "content": contexte
                    },

                    {
                        "role": "user",
                        "content": question
                    }
                ],

                "stream": False
            },

            timeout=120
        )

        reponse.raise_for_status()

        resultat = reponse.json()

        return resultat["message"]["content"]

    except requests.exceptions.ConnectionError:

        return (
            "Erreur : Ollama n'est pas accessible.\n\n"
            "Vérifiez qu'Ollama est installé et qu'il fonctionne."
        )

    except requests.exceptions.Timeout:

        return (
            "Erreur : Ollama met trop de temps à répondre. "
            "Le modèle est peut-être encore en cours de chargement."
        )

    except Exception as e:

        return f"Erreur lors de l'appel à Ollama : {e}"


class AssistantIAScreen(QWidget):

    def __init__(self, utilisateur):

        super().__init__()
        self.utilisateur = utilisateur

        layout = QVBoxLayout(self)

        layout.addWidget(TitrePage("Assistant IA", "Répond uniquement à partir des résultats déjà calculés par le système"))

        self.historique = QTextEdit()
        self.historique.setReadOnly(True)

        layout.addWidget(
            self.historique
        )

        ligne_saisie = QHBoxLayout()

        self.champ_question = QLineEdit()

        self.champ_question.setPlaceholderText(
            "Poser une question sur les résultats..."
        )

        bouton_envoyer = QPushButton(
            "Envoyer"
        )

        bouton_envoyer.clicked.connect(
            self.envoyer_question
        )

        self.champ_question.returnPressed.connect(
            self.envoyer_question
        )

        ligne_saisie.addWidget(
            self.champ_question
        )

        ligne_saisie.addWidget(
            bouton_envoyer
        )

        layout.addLayout(
            ligne_saisie
        )

    def envoyer_question(self):

        question = self.champ_question.text().strip()

        if not question:
            return

        self.historique.append(
            f"<p style='color:#0E4749'><b>🧑 Vous</b><br/>{question}</p>"
        )

        id_agence = (self.utilisateur["id_agence"]
                     if self.utilisateur["role"] == "agent" else None)
        reponse = interroger_assistant(
            question, id_agence
        )

        self.historique.append(
            f"<p><b>🤖 Assistant</b><br/>{reponse}</p><hr/>"
        )

        self.champ_question.clear()

