"""
Worker Gemini — utilise le CLI `gemini` déjà authentifié (compte Google).
Pas de clé API nécessaire.
"""
import subprocess
import re

GEMINI_BIN = "/home/analyst/.local/bin/gemini"


def run(task: str, context: str = "", model: str = None) -> str:
    prompt = f"Contexte:\n{context}\n\nTâche:\n{task}" if context else task

    cmd = [GEMINI_BIN, "--prompt", prompt]
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout.strip()
        # Retirer les warnings terminaux qui polluent la sortie
        lines = [l for l in output.splitlines()
                 if not l.startswith("Warning:") and not l.startswith("Ripgrep")]
        return "\n".join(lines).strip()
    except subprocess.TimeoutExpired:
        return "Erreur : timeout Gemini worker (>120s)"
    except Exception as e:
        return f"Erreur Gemini worker : {e}"
