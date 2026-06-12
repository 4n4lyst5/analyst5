"""
Authentification OpenAI — token de session extrait du compte web.
OpenAI n'a pas d'OAuth public standard pour les apps tierces.
On utilise le token de session web (obtenu depuis le navigateur une seule fois).
"""
import os
import json
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".analyst5" / "openai_token.json"


def is_authenticated() -> bool:
    return CREDENTIALS_PATH.exists()


def authenticate():
    """Enregistre le token OpenAI (session ou API key) de façon sécurisée."""
    print("""
Pour authentifier OpenAI :

Option A — API key (https://platform.openai.com/api-keys) :
  → Crée une clé et colle-la ici

Option B — Session token (depuis le navigateur) :
  → Ouvre https://chat.openai.com dans Firefox
  → F12 > Application > Cookies > https://chat.openai.com
  → Copie la valeur du cookie '__Secure-next-auth.session-token'
""")
    token = input("Colle ton token OpenAI ici : ").strip()
    if not token:
        print("Annulé.")
        return False

    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Détecter si c'est une API key (sk-...) ou un session token
    token_type = "api_key" if token.startswith("sk-") else "session_token"

    with open(CREDENTIALS_PATH, "w") as f:
        json.dump({"type": token_type, "token": token}, f)

    os.chmod(CREDENTIALS_PATH, 0o600)
    print(f"✓ OpenAI authentifié ({token_type}) — sauvegardé dans {CREDENTIALS_PATH}")
    return True


def get_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        raise RuntimeError("OpenAI non authentifié. Lance : analyst5 auth openai")
    with open(CREDENTIALS_PATH) as f:
        return json.load(f)
