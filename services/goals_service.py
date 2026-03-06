from pathlib import Path

from services.json_store import cargar_json, guardar_json, obtener_lock
from services.timezone_utils import ahora

GOALS_PATH = Path("data/metas.json")


def _siguiente_id(metas: list[dict]) -> int:
    if not metas:
        return 1
    return max(m["id"] for m in metas) + 1


def crear_meta(
    user_id: str,
    titulo: str,
    descripcion: str,
    pasos: list[str],
    fecha_limite: str | None = None,
) -> str:
    """Crea una meta con sus pasos."""
    lock = obtener_lock(GOALS_PATH)
    with lock:
        metas = cargar_json(GOALS_PATH)
        nueva = {
            "id": _siguiente_id(metas),
            "user_id": user_id,
            "titulo": titulo,
            "descripcion": descripcion,
            "pasos": [
                {
                    "num": i + 1,
                    "descripcion": paso,
                    "estado": "pendiente",
                    "notas": "",
                    "fecha_completado": None,
                }
                for i, paso in enumerate(pasos)
            ],
            "estado": "en_progreso",
            "fecha_creacion": ahora().strftime("%Y-%m-%d %H:%M"),
            "fecha_limite": fecha_limite,
        }
        metas.append(nueva)
        guardar_json(GOALS_PATH, metas)

    resumen_pasos = "\n".join(f"  {p['num']}. {p['descripcion']}" for p in nueva["pasos"])
    limite = f"\nFecha limite: {fecha_limite}" if fecha_limite else ""
    return (
        f"Meta #{nueva['id']} creada: {titulo}\n"
        f"Pasos:\n{resumen_pasos}{limite}"
    )


def ver_meta(user_id: str, meta_id: int) -> str:
    """Muestra el detalle de una meta con el estado de cada paso."""
    metas = cargar_json(GOALS_PATH)
    for m in metas:
        if m["id"] == meta_id and m["user_id"] == user_id:
            iconos = {"pendiente": "[ ]", "en_progreso": "[~]", "completado": "[x]"}
            pasos = []
            for p in m["pasos"]:
                icono = iconos.get(p["estado"], "[ ]")
                linea = f"  {icono} {p['num']}. {p['descripcion']}"
                if p["notas"]:
                    linea += f"\n      Nota: {p['notas']}"
                if p["fecha_completado"]:
                    linea += f"\n      Completado: {p['fecha_completado']}"
                pasos.append(linea)

            completados = sum(1 for p in m["pasos"] if p["estado"] == "completado")
            total = len(m["pasos"])
            progreso = f"{completados}/{total} pasos completados"
            limite = f"\nFecha limite: {m['fecha_limite']}" if m["fecha_limite"] else ""

            return (
                f"Meta #{m['id']}: {m['titulo']} [{m['estado']}]\n"
                f"{m['descripcion']}\n"
                f"Progreso: {progreso}{limite}\n\n"
                f"Pasos:\n" + "\n".join(pasos)
            )

    return f"No se encontro la meta #{meta_id}."


def listar_metas(user_id: str, solo_activas: bool = True) -> str:
    """Lista las metas de un usuario."""
    metas = cargar_json(GOALS_PATH)
    del_usuario = [m for m in metas if m["user_id"] == user_id]
    if solo_activas:
        del_usuario = [m for m in del_usuario if m["estado"] != "completada"]

    if not del_usuario:
        msg = "No tienes metas activas." if solo_activas else "No tienes metas registradas."
        return msg

    lineas = []
    for m in del_usuario:
        completados = sum(1 for p in m["pasos"] if p["estado"] == "completado")
        total = len(m["pasos"])
        lineas.append(
            f"#{m['id']} [{m['estado']}] {m['titulo']} ({completados}/{total} pasos)"
        )
    return "\n".join(lineas)


def actualizar_paso(
    user_id: str,
    meta_id: int,
    paso_num: int,
    nuevo_estado: str,
    notas: str = "",
) -> str:
    """Actualiza el estado de un paso de una meta.

    Estados: pendiente, en_progreso, completado
    """
    estados_validos = ("pendiente", "en_progreso", "completado")
    if nuevo_estado not in estados_validos:
        return f"ERROR: Estado '{nuevo_estado}' no valido. Debe ser: {', '.join(estados_validos)}."

    lock = obtener_lock(GOALS_PATH)
    with lock:
        metas = cargar_json(GOALS_PATH)
        for m in metas:
            if m["id"] == meta_id and m["user_id"] == user_id:
                for p in m["pasos"]:
                    if p["num"] == paso_num:
                        p["estado"] = nuevo_estado
                        if notas:
                            p["notas"] = notas
                        if nuevo_estado == "completado":
                            p["fecha_completado"] = ahora().strftime("%Y-%m-%d %H:%M")

                        todos_completados = all(
                            pa["estado"] == "completado" for pa in m["pasos"]
                        )
                        if todos_completados:
                            m["estado"] = "completada"

                        guardar_json(GOALS_PATH, metas)

                        completados = sum(
                            1 for pa in m["pasos"] if pa["estado"] == "completado"
                        )
                        total = len(m["pasos"])
                        msg = f"Paso {paso_num} de meta #{meta_id}: {nuevo_estado}"
                        if notas:
                            msg += f"\nNota: {notas}"
                        msg += f"\nProgreso: {completados}/{total}"
                        if todos_completados:
                            msg += "\n\nMeta completada!"
                        return msg

                return f"No se encontro el paso {paso_num} en la meta #{meta_id}."

    return f"No se encontro la meta #{meta_id}."


def agregar_paso(user_id: str, meta_id: int, descripcion: str) -> str:
    """Agrega un nuevo paso a una meta existente."""
    lock = obtener_lock(GOALS_PATH)
    with lock:
        metas = cargar_json(GOALS_PATH)
        for m in metas:
            if m["id"] == meta_id and m["user_id"] == user_id:
                nuevo_num = max(p["num"] for p in m["pasos"]) + 1 if m["pasos"] else 1
                m["pasos"].append({
                    "num": nuevo_num,
                    "descripcion": descripcion,
                    "estado": "pendiente",
                    "notas": "",
                    "fecha_completado": None,
                })
                if m["estado"] == "completada":
                    m["estado"] = "en_progreso"
                guardar_json(GOALS_PATH, metas)
                return f"Paso {nuevo_num} agregado a meta #{meta_id}: {descripcion}"

    return f"No se encontro la meta #{meta_id}."


def eliminar_meta(user_id: str, meta_id: int) -> str:
    """Elimina una meta."""
    lock = obtener_lock(GOALS_PATH)
    with lock:
        metas = cargar_json(GOALS_PATH)
        original = len(metas)
        metas = [m for m in metas if not (m["id"] == meta_id and m["user_id"] == user_id)]
        if len(metas) == original:
            return f"No se encontro la meta #{meta_id}."
        guardar_json(GOALS_PATH, metas)
    return f"Meta #{meta_id} eliminada."


def obtener_metas_para_prompt(user_id: str) -> str:
    """Devuelve las metas activas formateadas para incluir en el system prompt."""
    metas = cargar_json(GOALS_PATH)
    activas = [
        m for m in metas
        if m["user_id"] == user_id and m["estado"] != "completada"
    ]
    if not activas:
        return ""

    lineas = []
    for m in activas:
        completados = sum(1 for p in m["pasos"] if p["estado"] == "completado")
        total = len(m["pasos"])
        siguiente = next(
            (p for p in m["pasos"] if p["estado"] != "completado"), None
        )
        sig_desc = f" | Siguiente: {siguiente['descripcion']}" if siguiente else ""
        limite = f" | Limite: {m['fecha_limite']}" if m["fecha_limite"] else ""
        lineas.append(
            f"- Meta #{m['id']}: {m['titulo']} ({completados}/{total}){sig_desc}{limite}"
        )
    return "\n".join(lineas)
