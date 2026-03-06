from duckduckgo_search import DDGS


def buscar_web(consulta: str, max_resultados: int = 5) -> str:
    """Busca en internet usando DuckDuckGo y devuelve resultados formateados."""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(consulta, max_results=max_resultados))
    except Exception as e:
        return f"Error al buscar: {e}"

    if not resultados:
        return f"No se encontraron resultados para '{consulta}'."

    lineas = []
    for i, r in enumerate(resultados, 1):
        lineas.append(
            f"{i}. {r['title']}\n"
            f"   {r['body']}\n"
            f"   {r['href']}"
        )
    return "\n\n".join(lineas)


def buscar_noticias(consulta: str, max_resultados: int = 5) -> str:
    """Busca noticias recientes usando DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.news(consulta, max_results=max_resultados))
    except Exception as e:
        return f"Error al buscar noticias: {e}"

    if not resultados:
        return f"No se encontraron noticias sobre '{consulta}'."

    lineas = []
    for i, r in enumerate(resultados, 1):
        fecha = r.get("date", "sin fecha")
        lineas.append(
            f"{i}. {r['title']}\n"
            f"   {r['body']}\n"
            f"   Fuente: {r.get('source', 'desconocida')} | {fecha}\n"
            f"   {r['url']}"
        )
    return "\n\n".join(lineas)
