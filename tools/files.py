import os


def read(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"Fichier introuvable : {path}"
    with open(path, "r", errors="replace") as f:
        return f.read()


def write(path: str, content: str) -> str:
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"Écrit : {path}"


def list_dir(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"Dossier introuvable : {path}"
    entries = os.listdir(path)
    return "\n".join(sorted(entries))
