import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from app.db import engine
from ml.anomalies import detecter_anomalies
from ml.prevision import prevoir

styles = getSampleStyleSheet()

def generer_rapport_pdf(chemin_sortie: str = "rapport_performance.pdf"):
    story = [Paragraph("Rapport de performance commerciale", styles["Title"]), Spacer(1, 12)]

# --- KPI par agence ---
    kpi = pd.read_sql("""
        SELECT da.agence, COALESCE(SUM(f.montant),0) AS ca, COUNT(f.id_vente) AS nb_ventes
        FROM dim_agence da LEFT JOIN fait_vente f ON f.id_agence = da.id_agence
        GROUP BY da.agence ORDER BY ca DESC
    """, engine)

    story.append(Paragraph("Chiffre d'affaires par agence", styles["Heading2"]))
    data = [["Agence", "CA (M Ar)", "Nb ventes"]] + [
        [r["agence"], f"{r['ca']/1e6:,.0f}", str(int(r["nb_ventes"]))]
        for _, r in kpi.iterrows()
    ]
    table = Table(data, colWidths=[150, 100, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0E4749")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E1D8")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    # --- Anomalies ---
    story.append(Paragraph("Anomalies détectées", styles["Heading2"]))
    anomalies = detecter_anomalies(top_n=10)
    if anomalies.empty:
        story.append(Paragraph("Aucune anomalie significative détectée.", styles["Normal"]))
    else:
        data_an = [["Agence", "Produit", "Montant", "Score"]] + [
            [r["agence"], r["produit"], f"{r['montant']:,.0f} Ar", f"{r['ratio']:.1f}×"]
            for _, r in anomalies.iterrows()
        ]
        story.append(Table(data_an, colWidths=[90, 160, 90, 60]))
        
    doc = SimpleDocTemplate(chemin_sortie, pagesize=A4)
    doc.build(story)
    return chemin_sortie


if __name__ == "__main__":
    chemin = generer_rapport_pdf()
    print("Rapport généré :", chemin)
