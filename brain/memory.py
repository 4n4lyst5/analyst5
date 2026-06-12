import os
import re
from datetime import datetime
from config import MEMORY_DIR, MEMORY_INDEX


def load_memory() -> str:
    """Charge tout le contenu de la mémoire pour le contexte d'Analyst5."""
    if not os.path.exists(MEMORY_INDEX):
        return "Aucune mémoire disponible."

    sections = []

    # Lire l'index
    with open(MEMORY_INDEX, "r") as f:
        index = f.read()
    sections.append(f"=== INDEX MÉMOIRE ===\n{index}")

    # Extraire les liens vers les fichiers mémoire
    file_links = re.findall(r'\[.*?\]\((.*?\.md)\)', index)
    for fname in file_links:
        fpath = os.path.join(MEMORY_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "r") as f:
                content = f.read()
            sections.append(f"=== {fname.upper()} ===\n{content}")

    return "\n\n".join(sections)


def save_memory(filename: str, name: str, description: str, mem_type: str, content: str):
    """Sauvegarde une nouvelle entrée mémoire."""
    os.makedirs(MEMORY_DIR, exist_ok=True)

    filepath = os.path.join(MEMORY_DIR, filename)
    frontmatter = f"""---
name: {name}
description: {description}
metadata:
  type: {mem_type}
---

{content}
"""
    with open(filepath, "w") as f:
        f.write(frontmatter)

    # Mettre à jour l'index MEMORY.md
    index_path = MEMORY_INDEX
    entry = f"- [{description[:60]}]({filename}) — {description[:80]}\n"

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            index_content = f.read()
        if filename not in index_content:
            with open(index_path, "a") as f:
                f.write(entry)
    else:
        with open(index_path, "w") as f:
            f.write(f"# Memory Index\n\n{entry}")


def append_session_log(user_msg: str, analyst5_response: str):
    """Ajoute un log de session pour garder trace des échanges importants."""
    log_path = os.path.join(MEMORY_DIR, "session_logs.md")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"\n### {date}\n**User:** {user_msg[:200]}\n**Analyst5:** {analyst5_response[:400]}\n"

    with open(log_path, "a") as f:
        f.write(entry)
