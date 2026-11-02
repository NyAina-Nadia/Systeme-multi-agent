"""Envoi du résumé des alertes et recommandations par e-mail (SMTP)."""
import os
import smtplib
from email.message import EmailMessage

VARIABLES = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERTE_DESTINATAIRE"]


def configuration_manquante() -> list[str]:
    return [v for v in VARIABLES if not os.environ.get(v)]


def composer_message(recommandations: list[dict]) -> str:
    urgentes = [r for r in recommandations if r["priorite"] == "Haute"]
    autres = [r for r in recommandations if r["priorite"] == "Moyenne"]
    lignes = ["Synthèse automatique — Suivi de performance commerciale", ""]
    if urgentes:
        lignes.append(f"PRIORITÉ HAUTE ({len(urgentes)})")
        lignes += [f"- [{r['agence']}] {r['constat']} -> {r['action']}" for r in urgentes]
        lignes.append("")
    if autres:
        lignes.append(f"À SURVEILLER ({len(autres)})")
        lignes += [f"- [{r['agence']}] {r['constat']}" for r in autres]
    return "\n".join(lignes)


def envoyer_alertes(recommandations: list[dict]) -> bool:
    """Retourne False s'il n'y a rien d'urgent à envoyer. Lève ValueError si la configuration manque."""
    manquantes = configuration_manquante()
    if manquantes:
        raise ValueError("Variables manquantes dans .env : " + ", ".join(manquantes))
    importantes = [r for r in recommandations if r["priorite"] in ("Haute", "Moyenne")]
    if not importantes:
        return False
    msg = EmailMessage()
    msg["Subject"] = f"{sum(r['priorite'] == 'Haute' for r in importantes)} alerte(s) haute priorité — performance commerciale"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ["ALERTE_DESTINATAIRE"]
    msg.set_content(composer_message(importantes))
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587)), timeout=20) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)
    return True
