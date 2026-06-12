"""
Worker Claude — utilise le CLI `claude` déjà authentifié (compte Claude Code).
Pas de clé API nécessaire.
"""
import subprocess
import json


CLAUDE_BIN = "/home/analyst/.local/bin/claude"


def run(task: str, context: str = "", model: str = None) -> str:
    """Envoie une tâche au worker Claude via le CLI et retourne la réponse."""
    prompt = f"Contexte:\n{context}\n\nTâche:\n{task}" if context else task

    cmd = [CLAUDE_BIN, "--print", "--output-format", "text", "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 and result.stderr:
            return f"Erreur Claude worker : {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Erreur : timeout Claude worker (>120s)"
    except Exception as e:
        return f"Erreur Claude worker : {e}"
