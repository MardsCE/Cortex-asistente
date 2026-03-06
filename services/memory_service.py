from services.json_store import cargar_json, guardar_json, obtener_lock, user_data_path
from services.timezone_utils import ahora


def _path(user_id: str):
    return user_data_path(user_id, "memorias.json")


def _siguiente_id(memorias: list[dict]) -> int:
    if not memorias:
        return 1
    return max(m["id"] for m in memorias) + 1


def agregar_memoria(user_id: str, contenido: str, categoria: str = "general") -> str:
    """Agrega una memoria nueva."""
    path = _path(user_id)
    lock = obtener_lock(path)
    with lock:
        memorias = cargar_json(path)
        memoria = {
            "id": _siguiente_id(memorias),
            "contenido": contenido,
            "categoria": categoria,
            "fecha": ahora().strftime("%Y-%m-%d %H:%M"),
        }
        memorias.append(memoria)
        guardar_json(path, memorias)
    return f"Memoria #{memoria['id']} guardada: {contenido[:80]}"


def listar_memorias(user_id: str, categoria: str | None = None) -> str:
    """Lista todas las memorias, opcionalmente filtradas por categoria."""
    memorias = cargar_json(_path(user_id))
    if not memorias:
        return "No hay memorias guardadas."

    if categoria:
        memorias = [m for m in memorias if m["categoria"].lower() == categoria.lower()]
        if not memorias:
            return f"No hay memorias en la categoria '{categoria}'."

    lineas = []
    for m in memorias:
        lineas.append(
            f"#{m['id']} [{m['categoria']}] ({m['fecha']})\n"
            f"   {m['contenido']}"
        )
    return "\n\n".join(lineas)


def eliminar_memoria(user_id: str, memoria_id: int) -> str:
    """Elimina una memoria por su ID."""
    path = _path(user_id)
    lock = obtener_lock(path)
    with lock:
        memorias = cargar_json(path)
        nueva = [m for m in memorias if m["id"] != memoria_id]
        if len(nueva) == len(memorias):
            return f"No se encontro la memoria #{memoria_id}."
        guardar_json(path, nueva)
    return f"Memoria #{memoria_id} eliminada."


def buscar_memorias(user_id: str, termino: str) -> str:
    """Busca memorias por contenido o categoria."""
    memorias = cargar_json(_path(user_id))
    termino_lower = termino.lower()
    resultados = [
        m for m in memorias
        if termino_lower in m["contenido"].lower()
        or termino_lower in m["categoria"].lower()
    ]

    if not resultados:
        return f"No se encontraron memorias relacionadas con '{termino}'."

    lineas = []
    for m in resultados:
        lineas.append(f"#{m['id']} [{m['categoria']}] {m['contenido']}")
    return "\n".join(lineas)


def obtener_memorias_para_prompt(user_id: str) -> str:
    """Devuelve todas las memorias formateadas para incluir en el system prompt."""
    memorias = cargar_json(_path(user_id))
    if not memorias:
        return ""

    lineas = []
    for m in memorias:
        lineas.append(f"- [{m['categoria']}] {m['contenido']} ({m['fecha']})")
    return "\n".join(lineas)
