"""
Orchestrateur Analyst5 — boucle d'orchestration via le CLI claude (sans clé API).
Utilise un protocole JSON structuré pour simuler le tool_use.
"""
import subprocess
import json
import re
import os

from config import CLAUDE_BIN
from brain.personality import ANALYST5_SYSTEM_PROMPT
from brain.memory import load_memory, append_session_log
import workers.claude_worker as claude_worker
import workers.gemini_worker as gemini_worker
import workers.openai_worker as openai_worker
import tools.shell as shell_tool
import tools.search as search_tool
import tools.files as files_tool
from brain.memory import save_memory

ORCHESTRATOR_PROMPT = ANALYST5_SYSTEM_PROMPT + """

## Format de réponse

À chaque tour, tu dois répondre UNIQUEMENT avec un bloc JSON valide dans cette forme :

```json
{
  "thinking": "ton raisonnement court (1-2 phrases)",
  "action": "delegate_claude | delegate_gemini | delegate_openai | run_shell | web_search | read_file | write_file | save_memory | respond",
  "params": { ... },
  "final": false
}
```

Quand tu as terminé et veux répondre à l'utilisateur :
```json
{
  "thinking": "...",
  "action": "respond",
  "params": { "text": "ta réponse finale en markdown" },
  "final": true
}
```

### Params par action

- `delegate_claude`  : `{"task": "...", "context": "..."}`
- `delegate_gemini`  : `{"task": "...", "context": "..."}`
- `delegate_openai`  : `{"task": "...", "context": "..."}`
- `run_shell`        : `{"command": "...", "timeout": 30}`
- `web_search`       : `{"query": "...", "max_results": 5}`
- `read_file`        : `{"path": "..."}`
- `write_file`       : `{"path": "...", "content": "..."}`
- `save_memory`      : `{"filename": "...", "name": "...", "description": "...", "type": "project|user|feedback|reference", "content": "..."}`
- `respond`          : `{"text": "..."}`

Tu peux enchaîner autant d'actions que nécessaire avant de répondre. Réponds TOUJOURS avec du JSON pur, sans texte avant ou après.
"""


def _call_claude_cli(conversation: list[dict]) -> str:
    """Appelle le CLI claude avec l'historique de conversation formaté."""
    # Construire le prompt complet avec l'historique
    prompt_parts = []
    for msg in conversation:
        role = msg["role"].upper()
        content = msg["content"]
        prompt_parts.append(f"[{role}]\n{content}")

    full_prompt = "\n\n".join(prompt_parts)

    result = subprocess.run(
        [CLAUDE_BIN, "--print", "--output-format", "text",
         "--dangerously-skip-permissions",
         "--system-prompt", ORCHESTRATOR_PROMPT,
         full_prompt],
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout.strip()


def _parse_json_response(raw: str) -> dict:
    """Extrait le JSON de la réponse Claude."""
    # Chercher un bloc ```json ... ```
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Chercher du JSON brut
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Pas de JSON valide dans : {raw[:200]}")


def execute_action(action: str, params: dict, console=None) -> str:
    """Exécute une action et retourne le résultat."""
    def log(msg):
        if console:
            console.print(msg)

    if action == "delegate_claude":
        log(f"  [cyan]→ Claude[/cyan] : {params.get('task','')[:80]}...")
        return claude_worker.run(params.get("task", ""), params.get("context", ""))

    elif action == "delegate_gemini":
        log(f"  [blue]→ Gemini[/blue] : {params.get('task','')[:80]}...")
        return gemini_worker.run(params.get("task", ""), params.get("context", ""))

    elif action == "delegate_openai":
        log(f"  [green]→ OpenAI[/green] : {params.get('task','')[:80]}...")
        return openai_worker.run(params.get("task", ""), params.get("context", ""))

    elif action == "run_shell":
        cmd = params.get("command", "")
        log(f"  [yellow]→ Shell[/yellow] : {cmd}")
        result = shell_tool.run(cmd, params.get("timeout", 30))
        return result["stdout"] or result["stderr"] or "(pas de sortie)"

    elif action == "web_search":
        query = params.get("query", "")
        log(f"  [magenta]→ Web[/magenta] : {query}")
        results = search_tool.web_search(query, params.get("max_results", 5))
        return search_tool.format_results(results)

    elif action == "read_file":
        path = params.get("path", "")
        log(f"  [dim]→ Lecture[/dim] : {path}")
        return files_tool.read(path)

    elif action == "write_file":
        path = params.get("path", "")
        log(f"  [dim]→ Écriture[/dim] : {path}")
        return files_tool.write(path, params.get("content", ""))

    elif action == "save_memory":
        log(f"  [dim]→ Mémoire ↑[/dim] : {params.get('filename','')}")
        save_memory(
            params.get("filename", "untitled.md"),
            params.get("name", "untitled"),
            params.get("description", ""),
            params.get("type", "project"),
            params.get("content", ""),
        )
        return f"Mémorisé : {params.get('filename','')}"

    return f"Action inconnue : {action}"


def run(user_message: str, console=None) -> str:
    """Boucle d'orchestration complète pour un message utilisateur."""
    memory_context = load_memory()

    conversation = [
        {"role": "system_context", "content": f"MÉMOIRE:\n{memory_context}"},
        {"role": "user", "content": user_message},
    ]

    max_turns = 10
    for turn in range(max_turns):
        raw = _call_claude_cli(conversation)

        try:
            data = _parse_json_response(raw)
        except (ValueError, json.JSONDecodeError) as e:
            # Si Claude n'a pas suivi le format JSON, on prend la réponse brute
            append_session_log(user_message, raw)
            return raw

        thinking = data.get("thinking", "")
        action   = data.get("action", "respond")
        params   = data.get("params", {})
        is_final = data.get("final", False)

        if thinking and console:
            console.print(f"  [dim italic]{thinking}[/dim italic]")

        if action == "respond" or is_final:
            final_text = params.get("text", raw)
            append_session_log(user_message, final_text)
            return final_text

        # Exécuter l'action
        result = execute_action(action, params, console)

        # Ajouter le résultat à la conversation
        conversation.append({
            "role": "assistant",
            "content": raw,
        })
        conversation.append({
            "role": "tool_result",
            "content": f"Résultat de {action}:\n{result}",
        })

    return "Nombre maximum de tours atteint."
