import json
from pathlib import Path
from datetime import datetime

MEMORY_PATH = Path("data/memorias.json")


def _asegurar():
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("[]", encoding="utf-8")


def _cargar() -> list[dict]:
    _asegurar()
    return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))


def _guardar(memorias: list[dict]):
    _asegurar()
    MEMORY_PATH.write_text(
        json.dumps(memorias, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def agregar_memoria(contenido: str, categoria: str = "general") -> str:
    """Agrega una memoria nueva."""
    memorias = _cargar()

    memoria = {
        "id": len(memorias) + 1,
        "contenido": contenido,
        "categoria": categoria,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    memorias.append(memoria)
    _guardar(memorias)
    return f"Memoria #{memoria['id']} guardada: {contenido[:80]}"


def listar_memorias(categoria: str | None = None) -> str:
    """Lista todas las memorias, opcionalmente filtradas por categoria."""
    memorias = _cargar()
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


def eliminar_memoria(memoria_id: int) -> str:
    """Elimina una memoria por su ID."""
    memorias = _cargar()
    nueva = [m for m in memorias if m["id"] != memoria_id]

    if len(nueva) == len(memorias):
        return f"No se encontro la memoria #{memoria_id}."

    _guardar(nueva)
    return f"Memoria #{memoria_id} eliminada."


def buscar_memorias(termino: str) -> str:
    """Busca memorias por contenido o categoria."""
    memorias = _cargar()
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


def obtener_memorias_para_prompt() -> str:
    """Devuelve todas las memorias formateadas para incluir en el system prompt."""
    memorias = _cargar()
    if not memorias:
        return ""

    lineas = []
    for m in memorias:
        lineas.append(f"- [{m['categoria']}] {m['contenido']} ({m['fecha']})")
    return "\n".join(lineas)
