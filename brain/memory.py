import os
import re
from datetime import datetime
from config import MEMORY_DIR, MEMORY_INDEX

# Limites pour éviter de saturer le contexte
_MAX_FILE_CHARS  = 800   # max par fichier mémoire
_MAX_TOTAL_CHARS = 6000  # cap total mémoire injectée
_SKIP_FILES = {"session_logs.md"}  # fichiers exclus du contexte (trop verbeux)


def load_memory() -> str:
    """Charge la mémoire de façon sélective : index complet + extraits des fichiers."""
    if not os.path.exists(MEMORY_INDEX):
        return "Aucune mémoire disponible."

    with open(MEMORY_INDEX, "r") as f:
        index = f.read()

    sections = [f"=== INDEX ===\n{index}"]
    total = len(sections[0])

    file_links = re.findall(r'\[.*?\]\((.*?\.md)\)', index)
    for fname in file_links:
        if fname in _SKIP_FILES:
            continue
        fpath = os.path.join(MEMORY_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r") as f:
            content = f.read()
        excerpt = content[:_MAX_FILE_CHARS]
        if len(content) > _MAX_FILE_CHARS:
            excerpt += "\n[…tronqué]"
        chunk = f"=== {fname.upper()} ===\n{excerpt}"
        if total + len(chunk) > _MAX_TOTAL_CHARS:
            break
        sections.append(chunk)
        total += len(chunk)

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


_MAX_LOG_ENTRIES = 20


def append_session_log(user_msg: str, analyst5_response: str):
    """Log tournant des échanges — max 20 entrées, les plus anciens effacés."""
    log_path = os.path.join(MEMORY_DIR, "session_logs.md")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"### {date}\n**User:** {user_msg[:200]}\n**Analyst5:** {analyst5_response[:400]}\n"

    existing = ""
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            existing = f.read()

    # Découper en blocs par entrée (séparateur = "### ")
    entries = [e for e in re.split(r'(?=### \d{4}-\d{2}-\d{2})', existing) if e.strip()]
    entries.append(new_entry)

    # Garder seulement les N dernières
    entries = entries[-_MAX_LOG_ENTRIES:]

    with open(log_path, "w") as f:
        f.write("# Session logs\n\n" + "\n".join(entries))
