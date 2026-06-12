"""
Worker OpenAI — utilise le CLI `codex` déjà authentifié (compte OpenAI).
Pas de clé API nécessaire.
"""
import subprocess
import tempfile
import os

CODEX_BIN = os.path.expanduser("~/.local/bin/codex")


def run(task: str, context: str = "", model: str = None) -> str:
    prompt = f"Contexte:\n{context}\n\nTâche:\n{task}" if context else task

    cmd = [CODEX_BIN, "exec", "--skip-git-repo-check", "--ephemeral"]
    if model:
        cmd += ["-m", model]

    with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as f:
        outfile = f.name

    cmd += ["-o", outfile, prompt]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        with open(outfile) as f:
            result = f.read().strip()
        return result if result else "Pas de réponse."
    except subprocess.TimeoutExpired:
        return "Erreur : timeout Codex worker (>120s)"
    except Exception as e:
        return f"Erreur Codex worker : {e}"
    finally:
        try:
            os.unlink(outfile)
        except Exception:
            pass
