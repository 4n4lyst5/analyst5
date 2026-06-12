from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Recherche web via DuckDuckGo. Retourne une liste de {title, url, body}."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url":   r.get("href", ""),
                "body":  r.get("body", ""),
            })
    return results


def format_results(results: list[dict]) -> str:
    """Formate les résultats pour les passer en contexte à un worker."""
    if not results:
        return "Aucun résultat trouvé."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\nURL: {r['url']}\n{r['body']}\n")
    return "\n".join(lines)
