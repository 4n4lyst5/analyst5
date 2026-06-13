#!/usr/bin/env python3
"""
Telegram bot pour Analyst5.
Chaque chat maintient sa propre session Claude avec continuité.
"""
import os, sys, json, logging, threading, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import telebot
from brain.memory import load_memory, append_session_log
from analyst5 import ask_with_session

# ─── Config ────────────────────────────────────────────────────────────────────

CONFIG_FILE   = Path.home() / ".analyst5" / "telegram_config.json"
SESSIONS_FILE = Path.home() / ".analyst5" / "telegram_sessions.json"

def _load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def _load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        return json.loads(SESSIONS_FILE.read_text())
    return {}

def _save_sessions(s: dict):
    SESSIONS_FILE.write_text(json.dumps(s))

config   = _load_config()
TOKEN    = config["token"]
ALLOWED  = set(str(u) for u in config.get("allowed_users", []))

bot      = telebot.TeleBot(TOKEN, parse_mode=None, threaded=True)
sessions = _load_sessions()

# ─── Sécurité ──────────────────────────────────────────────────────────────────

def allowed(message) -> bool:
    if not ALLOWED:
        return True
    return str(message.from_user.id) in ALLOWED

# ─── Typing indicator en boucle ────────────────────────────────────────────────

def keep_typing(chat_id: int, stop_event: threading.Event):
    while not stop_event.is_set():
        try:
            bot.send_chat_action(chat_id, "typing")
        except Exception:
            pass
        stop_event.wait(4)

# ─── Envoi réponse (texte + images éventuelles) ────────────────────────────────

def send_response(chat_id: int, response: str):
    # Chercher IMAGE_READY:/chemin dans la réponse
    image_paths = re.findall(r'IMAGE_READY:(\S+)', response)
    # Nettoyer le texte des marqueurs IMAGE_READY
    text = re.sub(r'IMAGE_READY:\S+', '', response).strip()

    # Envoyer le texte si non vide
    if text:
        for chunk in [text[i:i+4096] for i in range(0, max(len(text), 1), 4096)]:
            bot.send_message(chat_id, chunk)

    # Envoyer les images générées
    for path in image_paths:
        path = path.strip()
        if os.path.exists(path):
            with open(path, "rb") as f:
                bot.send_photo(chat_id, f)
            os.remove(path)

# ─── Commandes ─────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    uid  = message.from_user.id
    cid  = message.chat.id
    name = message.from_user.first_name or "toi"
    bot.send_message(cid,
        f"Analyst5 en ligne ✓\n\n"
        f"Ton user_id : {uid}\n"
        f"Ton chat_id : {cid}\n\n"
        f"Commandes :\n"
        f"/reset — nouvelle session\n"
        f"/status — état des workers\n\n"
        f"Parle-moi, {name} !")

@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    if not allowed(message):
        bot.reply_to(message, "Accès non autorisé.")
        return
    cid = str(message.chat.id)
    if cid in sessions:
        del sessions[cid]
        _save_sessions(sessions)
    bot.reply_to(message, "Session réinitialisée.")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if not allowed(message):
        bot.reply_to(message, "Accès non autorisé.")
        return
    import subprocess, sys as _sys
    script = str(Path(__file__).parent.parent / "analyst5.py")
    r = subprocess.run(
        [_sys.executable, script, "status"],
        capture_output=True, text=True, timeout=30
    )
    bot.send_message(message.chat.id, r.stdout[-3000:] or "Erreur")

# ─── Messages ──────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def handle(message):
    if not allowed(message):
        bot.reply_to(message, "Accès non autorisé.")
        return

    cid       = str(message.chat.id)
    user_text = message.text or ""
    if not user_text.strip():
        return

    # Si l'utilisateur répond à un message spécifique, inclure le contexte
    if message.reply_to_message:
        quoted = message.reply_to_message.text or message.reply_to_message.caption or ""
        if quoted:
            user_text = f"[En réponse à ce message : \"{quoted[:500]}\"]\n\n{user_text}"

    stop_typing = threading.Event()
    t = threading.Thread(target=keep_typing, args=(message.chat.id, stop_typing), daemon=True)
    t.start()

    try:
        memory_context = load_memory()
        session_id     = sessions.get(cid)
        response, new_sid = ask_with_session(user_text, memory_context, session_id)
        sessions[cid] = new_sid
        _save_sessions(sessions)
        append_session_log(user_text, response)
    except Exception as e:
        response = f"Erreur : {e}"
    finally:
        stop_typing.set()

    send_response(message.chat.id, response)

# ─── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    print("Analyst5 Telegram bot démarré — en attente de messages...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
