"""
Authentification Gemini via compte Google — OAuth 2.0 navigateur.
Première utilisation : ouvre le navigateur, demande de se connecter avec Google.
Les credentials sont sauvegardés dans ~/.analyst5/gemini_token.json pour les sessions suivantes.
"""
import os
import json
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".analyst5" / "gemini_token.json"
# Scopes Google AI Studio
SCOPES = ["https://www.googleapis.com/auth/generative-language"]

# Client ID public de Google AI Studio (usage personnel, pas de secret requis)
# L'utilisateur devra créer un OAuth client dans Google Cloud Console
OAUTH_CLIENT_FILE = Path.home() / ".analyst5" / "gemini_client.json"


def is_authenticated() -> bool:
    return CREDENTIALS_PATH.exists()


def authenticate():
    """Lance le flow OAuth Google dans le navigateur."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not OAUTH_CLIENT_FILE.exists():
        print(f"""
Pour authentifier Gemini avec ton compte Google :

1. Va sur https://console.cloud.google.com/
2. Crée un projet ou sélectionne un existant
3. Active l'API "Generative Language API"
4. Crée des identifiants OAuth 2.0 (type : Application de bureau)
5. Télécharge le JSON et sauvegarde-le ici : {OAUTH_CLIENT_FILE}
6. Relance `analyst5 auth gemini`
""")
        return False

    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    with open(CREDENTIALS_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"✓ Gemini authentifié — credentials sauvegardés dans {CREDENTIALS_PATH}")
    return True


def get_credentials():
    """Charge et rafraîchit les credentials Google."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not CREDENTIALS_PATH.exists():
        raise RuntimeError("Gemini non authentifié. Lance : analyst5 auth gemini")

    creds = Credentials.from_authorized_user_file(str(CREDENTIALS_PATH), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(CREDENTIALS_PATH, "w") as f:
            f.write(creds.to_json())

    return creds
