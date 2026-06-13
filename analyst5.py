#!/usr/bin/env python3
"""
Analyst5 — Super-agent orchestrateur
Usage :
  analyst5                    → session interactive
  analyst5 -p "prompt"        → one-shot non-interactif
  analyst5 status             → état des workers
  analyst5 auth gemini|openai → info d'authentification
"""
import sys
import os
import subprocess
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

from config import CLAUDE_BIN, GEMINI_BIN, CODEX_BIN
from brain.personality import ANALYST5_SYSTEM_PROMPT
from brain.memory import load_memory, append_session_log

console = Console()


def ask_with_session(user_message: str, memory_context: str, session_id: str = None) -> tuple[str, str]:
    """
    Envoie un message à Claude avec continuité de session.
    Retourne (réponse, session_id) pour chaîner les tours.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    system = ANALYST5_SYSTEM_PROMPT.replace("{{BASE_DIR}}", base_dir) + f"\n\n## Mémoire\n\n{memory_context}"

    cmd = [
        CLAUDE_BIN,
        "--print",
        "--output-format", "json",
        "--max-turns", "15",
        "--append-system-prompt", system,
    ]
    if os.getuid() != 0:
        cmd.append("--dangerously-skip-permissions")

    if session_id:
        cmd += ["--resume", session_id]

    cmd.append(user_message)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    try:
        data = json.loads(result.stdout)
        response = data.get("result", "").strip()
        new_session_id = data.get("session_id", session_id or "")
        return response or result.stderr.strip(), new_session_id
    except (json.JSONDecodeError, AttributeError):
        return result.stdout.strip() or result.stderr.strip(), session_id or ""


# ─── Status ─────────────────────────────────────────────────────────────────

def _claude_ok() -> bool:
    try:
        with open(os.path.expanduser("~/.claude.json")) as f:
            d = json.load(f)
        return bool(d.get("oauthAccount"))
    except Exception:
        return False


def _gemini_ok() -> bool:
    gemini_home = os.path.expanduser("~/.gemini")
    return os.path.exists(GEMINI_BIN) and os.path.isdir(gemini_home)


def _codex_ok() -> bool:
    codex_home = os.path.expanduser("~/.codex")
    return os.path.exists(CODEX_BIN) and os.path.isdir(codex_home)


def _gmail_ok() -> bool:
    from pathlib import Path
    return (Path.home() / ".analyst5" / "gmail_creds.json").exists()


def cmd_status():
    table = Table(title="État des workers Analyst5", border_style="cyan")
    table.add_column("Capacité", style="bold")
    table.add_column("Statut")
    table.add_column("Auth")
    table.add_row("Claude",
                  "[green]✓ connecté[/green]" if _claude_ok() else "[red]✗[/red]",
                  "compte Claude Code (CLI)")
    table.add_row("Gemini",
                  "[green]✓ connecté[/green]" if _gemini_ok() else "[red]✗[/red]",
                  "compte Google (gemini CLI)" if _gemini_ok() else "lance: gemini")
    table.add_row("OpenAI",
                  "[green]✓ connecté[/green]" if _codex_ok() else "[red]✗[/red]",
                  "compte OpenAI (codex CLI)" if _codex_ok() else "lance: codex login")
    table.add_row("Gmail",
                  "[green]✓ connecté[/green]" if _gmail_ok() else "[yellow]⚠ non auth[/yellow]",
                  "compte Google (OAuth)" if _gmail_ok() else "lance: analyst5 auth gmail")
    console.print(table)


def cmd_auth(provider: str):
    if provider == "claude":
        status = "[green]✓ connecté[/green]" if _claude_ok() else "[red]✗ non connecté[/red]"
        console.print(f"Claude : {status} (via compte Claude Code)")
    elif provider == "gemini":
        console.print("Gemini utilise son propre CLI. Lance : [cyan]~/.local/bin/gemini[/cyan]")
    elif provider == "openai":
        console.print("OpenAI utilise Codex CLI. Lance : [cyan]~/.local/bin/codex login[/cyan]")
    elif provider == "gmail":
        from tools.gmail import authenticate, is_authenticated
        if is_authenticated():
            console.print("[green]✓ Gmail déjà authentifié[/green]")
        else:
            authenticate()
    else:
        console.print(f"[red]Provider inconnu : {provider}[/red]")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if args and args[0] == "status":
        cmd_status()
        return

    if len(args) >= 2 and args[0] == "auth":
        cmd_auth(args[1])
        return

    # Charger la mémoire une seule fois
    memory_context = load_memory()

    # Mode non-interactif : analyst5 -p "prompt"
    if len(args) >= 2 and args[0] in ("-p", "--prompt"):
        prompt = " ".join(args[1:])
        console.print(f"[bold yellow]Analyst5[/bold yellow] [dim]→ traitement...[/dim]")
        response, _ = ask_with_session(prompt, memory_context)
        console.print(Markdown(response))
        append_session_log(prompt, response)
        return

    # Session interactive
    console.print(Panel(
        "[bold cyan]ANALYST5[/bold cyan] [dim]— Super-agent orchestrateur[/dim]\n"
        "[dim]`status` pour voir les workers · `exit` pour quitter[/dim]",
        border_style="cyan",
    ))
    console.print("[dim]Mémoire chargée ✓[/dim]\n")

    session_id = None  # maintenu tout au long de la session

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]Vous[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Analyst5 hors ligne.[/dim]")
            break

        cmd = user_input.strip().lower()
        if cmd in ("exit", "quit", "q"):
            console.print("[dim]Analyst5 hors ligne.[/dim]")
            break
        if cmd == "status":
            cmd_status()
            continue
        if not user_input.strip():
            continue

        console.print("[bold yellow]Analyst5[/bold yellow] [dim]→ traitement...[/dim]")

        try:
            response, session_id = ask_with_session(user_input, memory_context, session_id)
            console.print(f"\n[bold yellow]Analyst5[/bold yellow]")
            console.print(Markdown(response))
            append_session_log(user_input, response)
            memory_context = load_memory()
        except subprocess.TimeoutExpired:
            console.print("[red]Timeout — la tâche a pris trop de temps.[/red]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/red]")


if __name__ == "__main__":
    main()
