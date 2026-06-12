# Analyst5

**Super-agent orchestrateur CLI** — un seul point d'entrée qui commande Claude, Gemini et OpenAI pour accomplir des missions complexes.

Analyst5 ne fait pas le travail lui-même. Il analyse, décide, délègue aux bons workers IA, et consolide les résultats. Il a une mémoire persistante et un accès complet au système local.

---

## Architecture

```
analyst5
├── Orchestrateur (Claude CLI)
│   └── Personnalité + mémoire chargées au démarrage
├── Workers
│   ├── Claude  → raisonnement, sécurité, pentest, analyse
│   ├── Gemini  → recherche web, résumé, long contexte
│   └── OpenAI  → code, fonctions, mathématiques
└── Capacités système
    ├── Shell   → exécution de commandes sur le PC
    ├── Web     → recherches en temps réel (DuckDuckGo)
    └── Mémoire → persistance entre sessions
```

```
Vous → analyst5 "fais X"
            ↓
       analyse la tâche
       décide qui fait quoi
            ↓
    ┌───────┬───────┬───────┐
  Claude  Gemini  OpenAI  Shell
    └───────┴───────┴───────┘
            ↓
     consolide + mémorise
            ↓
          Vous ←
```

---

## Prérequis

- Python 3.10+
- [Claude Code CLI](https://claude.ai/code) — installé et authentifié
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) — installé et authentifié
- [Codex CLI](https://github.com/openai/codex) — installé et authentifié

---

## Installation

```bash
git clone https://github.com/4n4lyst5/analyst5.git
cd analyst5
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chmod +x analyst5

# Rendre accessible depuis n'importe où
ln -sf "$(pwd)/analyst5" ~/.local/bin/analyst5
```

---

## Authentification des workers

Analyst5 utilise les CLIs officiels de chaque provider — **aucune clé API à stocker**.

### Claude
```bash
# Déjà connecté si Claude Code CLI est installé
claude auth status
```

### Gemini
```bash
# Installe et connecte le CLI Gemini
npm install -g @google/gemini-cli --prefix ~/.local
gemini  # ouvre le navigateur pour l'authentification Google
```

### OpenAI (Codex)
```bash
# Installe et connecte le CLI Codex
npm install -g @openai/codex --prefix ~/.local
codex login  # ouvre le navigateur pour l'authentification OpenAI
```

---

## Utilisation

```bash
# Session interactive
analyst5

# One-shot non-interactif
analyst5 -p "analyse ce domaine example.com"

# État des workers
analyst5 status

# Info d'authentification
analyst5 auth claude
analyst5 auth gemini
analyst5 auth openai
```

---

## Exemples

```bash
# Recherche et analyse
analyst5 -p "cherche les dernières CVE critiques sur Nginx et fais un résumé"

# Tâche multi-workers
analyst5 -p "recherche les meilleures pratiques SOC 2025 et génère un rapport"

# Commandes système
analyst5 -p "liste les ports ouverts sur 192.168.1.1 et analyse les résultats"

# Mémoire persistante
analyst5 -p "qu'est-ce que tu sais sur SHIDORI ?"
```

---

## Structure du projet

```
analyst5/
├── analyst5            # Script de lancement (bash)
├── analyst5.py         # Point d'entrée principal
├── config.py           # Chemins des binaires CLI
├── brain/
│   ├── personality.py  # System prompt + personnalité d'Analyst5
│   └── memory.py       # Lecture/écriture mémoire persistante
├── workers/
│   ├── claude_worker.py   # Délégation → claude CLI
│   ├── gemini_worker.py   # Délégation → gemini CLI
│   └── openai_worker.py   # Délégation → codex CLI
├── tools/
│   ├── shell.py        # Exécution bash
│   ├── search.py       # Recherche web DuckDuckGo
│   └── files.py        # Opérations fichiers
└── requirements.txt
```

---

## Mémoire

Analyst5 charge et met à jour automatiquement sa mémoire depuis :
```
~/.claude/projects/-home-analyst/memory/
```

Chaque session importante, finding, ou décision est mémorisée sans intervention manuelle.

---

## Licence

MIT
