"""
Gmail tool pour Analyst5 — SMTP (envoi) + IMAP (lecture).
Auth via mot de passe d'application Google (pas d'OAuth requis).
Credentials stockés dans ~/.analyst5/gmail_creds.json
"""
import os
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from pathlib import Path

CREDS_PATH = Path.home() / ".analyst5" / "gmail_creds.json"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993


def is_authenticated() -> bool:
    return CREDS_PATH.exists()


def authenticate():
    """Enregistre l'adresse Gmail et le mot de passe d'application."""
    print("""
Pour connecter Gmail à Analyst5 :

1. Va sur https://myaccount.google.com/apppasswords
   (la 2FA doit être activée sur ton compte Google)
2. Crée un mot de passe d'application → nom : "Analyst5"
3. Copie le mot de passe généré (16 caractères)
""")
    gmail_addr = input("Ton adresse Gmail : ").strip()
    app_password = input("Mot de passe d'application (16 cars) : ").strip().replace(" ", "")

    CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDS_PATH, "w") as f:
        json.dump({"email": gmail_addr, "password": app_password}, f)
    os.chmod(CREDS_PATH, 0o600)
    print(f"✓ Gmail configuré pour {gmail_addr}")
    return True


def _load_creds() -> dict:
    if not CREDS_PATH.exists():
        raise RuntimeError("Gmail non configuré. Lance : analyst5 auth gmail")
    with open(CREDS_PATH) as f:
        return json.load(f)


def send_email(to: str, subject: str, body: str) -> str:
    """Envoie un email via SMTP."""
    creds = _load_creds()
    msg = MIMEMultipart("alternative")
    msg["From"]    = creds["email"]
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(creds["email"], creds["password"])
        server.sendmail(creds["email"], to, msg.as_string())

    return f"✓ Email envoyé à {to} — Objet : {subject}"


def get_recent_emails(max_results: int = 10, folder: str = "INBOX", unread_only: bool = True) -> list[dict]:
    """Lit les emails via IMAP."""
    creds = _load_creds()
    emails = []

    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(creds["email"], creds["password"])
        imap.select(folder)

        criteria = "UNSEEN" if unread_only else "ALL"
        _, msg_ids = imap.search(None, criteria)

        ids = msg_ids[0].split()
        # Prendre les N plus récents
        for msg_id in reversed(ids[-max_results:]):
            _, msg_data = imap.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            emails.append({
                "id":      msg_id.decode(),
                "from":    _decode_header(msg.get("From", "")),
                "to":      _decode_header(msg.get("To", "")),
                "subject": _decode_header(msg.get("Subject", "(sans objet)")),
                "date":    msg.get("Date", ""),
                "body":    _extract_body(msg)[:3000],
            })

    return emails


def format_emails_for_context(emails: list[dict]) -> str:
    if not emails:
        return "Aucun email trouvé."
    lines = []
    for i, e in enumerate(emails, 1):
        lines.append(
            f"[{i}] De: {e['from']}\n"
            f"    Objet: {e['subject']}\n"
            f"    Date: {e['date']}\n"
            f"    ---\n"
            f"    {e['body'][:500]}\n"
        )
    return "\n".join(lines)


def _decode_header(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    return ""
