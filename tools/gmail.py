"""
Gmail tool pour Analyst5 — envoyer, lire, résumer des emails.
Auth OAuth Google stockée dans ~/.analyst5/gmail_token.json
"""
import os
import json
import base64
import re
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

CREDENTIALS_PATH = Path.home() / ".analyst5" / "gmail_token.json"
CLIENT_FILE      = Path.home() / ".analyst5" / "gmail_client.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def is_authenticated() -> bool:
    return CREDENTIALS_PATH.exists()


def authenticate():
    """Lance le flow OAuth Google pour Gmail (ouvre le navigateur)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_FILE.exists():
        # Créer un client OAuth minimal via la console Google
        print(f"""
Pour connecter Gmail à Analyst5 :

1. Va sur https://console.cloud.google.com/
2. Crée un projet (ou réutilise un existant)
3. Active l'API Gmail
4. Crée des identifiants OAuth 2.0 → Application de bureau
5. Télécharge le JSON → sauvegarde ici : {CLIENT_FILE}
6. Relance : analyst5 auth gmail

Alternative rapide : utilise le fichier OAuth Gemini si tu en as un.
""")
        return False

    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    with open(CREDENTIALS_PATH, "w") as f:
        f.write(creds.to_json())
    os.chmod(CREDENTIALS_PATH, 0o600)
    print(f"✓ Gmail authentifié — token sauvegardé dans {CREDENTIALS_PATH}")
    return True


def _get_service():
    """Retourne le service Gmail API authentifié."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not CREDENTIALS_PATH.exists():
        raise RuntimeError("Gmail non authentifié. Lance : analyst5 auth gmail")

    creds = Credentials.from_authorized_user_file(str(CREDENTIALS_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(CREDENTIALS_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str, reply_to_id: str = None) -> str:
    """Envoie un email. Retourne l'ID du message envoyé."""
    service = _get_service()

    msg = MIMEMultipart("alternative")
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if reply_to_id:
        msg["In-Reply-To"] = reply_to_id
        msg["References"]  = reply_to_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw, **({"threadId": reply_to_id} if reply_to_id else {})}
    ).execute()

    return f"Email envoyé — ID : {result['id']}"


def get_recent_emails(max_results: int = 10, query: str = "is:unread") -> list[dict]:
    """Récupère les emails récents. Retourne une liste de dicts."""
    service = _get_service()

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        body = _extract_body(msg["payload"])

        emails.append({
            "id":      msg["id"],
            "thread":  msg["threadId"],
            "from":    headers.get("From", ""),
            "to":      headers.get("To", ""),
            "subject": headers.get("Subject", "(sans objet)"),
            "date":    headers.get("Date", ""),
            "body":    body[:2000],
            "snippet": msg.get("snippet", ""),
        })

    return emails


def get_thread(thread_id: str) -> list[dict]:
    """Récupère tous les messages d'un fil de discussion."""
    service = _get_service()
    thread = service.users().threads().get(userId="me", id=thread_id).execute()

    messages = []
    for msg in thread.get("messages", []):
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        messages.append({
            "id":      msg["id"],
            "from":    headers.get("From", ""),
            "date":    headers.get("Date", ""),
            "subject": headers.get("Subject", ""),
            "body":    _extract_body(msg["payload"])[:3000],
        })
    return messages


def mark_as_read(message_id: str):
    """Marque un email comme lu."""
    service = _get_service()
    service.users().messages().modify(
        userId="me", id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def format_emails_for_context(emails: list[dict]) -> str:
    """Formate les emails pour les passer en contexte à un worker IA."""
    if not emails:
        return "Aucun email trouvé."
    lines = []
    for i, e in enumerate(emails, 1):
        lines.append(
            f"[{i}] De: {e['from']}\n"
            f"    Objet: {e['subject']}\n"
            f"    Date: {e['date']}\n"
            f"    ID: {e['id']} | Thread: {e['thread']}\n"
            f"    {e['snippet']}\n"
        )
    return "\n".join(lines)


def _extract_body(payload: dict) -> str:
    """Extrait le corps texte d'un message Gmail."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part.get("body", {}).get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if part["mimeType"] == "text/html":
                data = part.get("body", {}).get("data", "")
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                return re.sub(r"<[^>]+>", " ", html).strip()
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""
