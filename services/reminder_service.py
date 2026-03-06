import json
from pathlib import Path
from datetime import datetime

REMINDERS_PATH = Path("data/recordatorios.json")


def _asegurar():
    REMINDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REMINDERS_PATH.exists():
        REMINDERS_PATH.write_text("[]", encoding="utf-8")


def _cargar() -> list[dict]:
    _asegurar()
    return json.loads(REMINDERS_PATH.read_text(encoding="utf-8"))


def _guardar(recordatorios: list[dict]):
    _asegurar()
    REMINDERS_PATH.write_text(
        json.dumps(recordatorios, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _siguiente_id(recordatorios: list[dict]) -> int:
    if not recordatorios:
        return 1
    return max(r["id"] for r in recordatorios) + 1


def crear_recordatorio(
    user_id: str,
    chat_id: str,
    contenido: str,
    tipo: str,
    hora: str,
    dia_semana: int | None = None,
    dias_intervalo: int | None = None,
    fecha_unica: str | None = None,
) -> str:
    """Crea un nuevo recordatorio.

    Tipos: unico, diario, semanal, cada_x_dias
    """
    # Validaciones estrictas - rechazar si falta informacion
    if not contenido or not contenido.strip():
        return "ERROR: Falta el contenido del recordatorio. Pregunta al usuario que quiere recordar."
    if not hora or not hora.strip():
        return "ERROR: Falta la hora. Pregunta al usuario a que hora quiere el recordatorio (formato HH:MM)."
    if tipo not in ("unico", "diario", "semanal", "cada_x_dias"):
        return f"ERROR: Tipo '{tipo}' no valido. Debe ser: unico, diario, semanal o cada_x_dias."
    if tipo == "unico" and not fecha_unica:
        return "ERROR: Para recordatorio unico falta la fecha (YYYY-MM-DD). Pregunta al usuario."
    if tipo == "semanal" and dia_semana is None:
        return "ERROR: Para recordatorio semanal falta el dia de la semana (0=lunes a 6=domingo). Pregunta al usuario."
    if tipo == "cada_x_dias" and not dias_intervalo:
        return "ERROR: Para recordatorio cada X dias falta el intervalo. Pregunta al usuario cada cuantos dias."

    recordatorios = _cargar()
    nuevo = {
        "id": _siguiente_id(recordatorios),
        "user_id": user_id,
        "chat_id": chat_id,
        "contenido": contenido,
        "tipo": tipo,
        "hora": hora,
        "dia_semana": dia_semana,
        "dias_intervalo": dias_intervalo,
        "fecha_unica": fecha_unica,
        "activo": True,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ultima_ejecucion": None,
    }
    recordatorios.append(nuevo)
    _guardar(recordatorios)

    desc_tipo = {
        "unico": f"una vez el {fecha_unica}",
        "diario": "todos los dias",
        "semanal": f"cada semana (dia {dia_semana})",
        "cada_x_dias": f"cada {dias_intervalo} dias",
    }
    return (
        f"Recordatorio #{nuevo['id']} creado: {contenido}\n"
        f"Frecuencia: {desc_tipo.get(tipo, tipo)} a las {hora}"
    )


def listar_recordatorios(user_id: str) -> str:
    """Lista los recordatorios de un usuario."""
    recordatorios = _cargar()
    del_usuario = [r for r in recordatorios if r["user_id"] == user_id]

    if not del_usuario:
        return "No tienes recordatorios configurados."

    lineas = []
    for r in del_usuario:
        estado = "Activo" if r["activo"] else "Pausado"
        tipo_desc = r["tipo"]
        if r["tipo"] == "semanal":
            dias = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
            tipo_desc = f"semanal ({dias[r['dia_semana']]})"
        elif r["tipo"] == "cada_x_dias":
            tipo_desc = f"cada {r['dias_intervalo']} dias"
        elif r["tipo"] == "unico":
            tipo_desc = f"unico ({r['fecha_unica']})"

        lineas.append(
            f"#{r['id']} [{estado}] {r['contenido']}\n"
            f"   {tipo_desc} a las {r['hora']}"
        )
    return "\n\n".join(lineas)


def eliminar_recordatorio(user_id: str, recordatorio_id: int) -> str:
    """Elimina un recordatorio."""
    recordatorios = _cargar()
    original = len(recordatorios)
    recordatorios = [
        r for r in recordatorios
        if not (r["id"] == recordatorio_id and r["user_id"] == user_id)
    ]

    if len(recordatorios) == original:
        return f"No se encontro el recordatorio #{recordatorio_id}."

    _guardar(recordatorios)
    return f"Recordatorio #{recordatorio_id} eliminado."


def toggle_recordatorio(user_id: str, recordatorio_id: int) -> str:
    """Activa o pausa un recordatorio."""
    recordatorios = _cargar()
    for r in recordatorios:
        if r["id"] == recordatorio_id and r["user_id"] == user_id:
            r["activo"] = not r["activo"]
            _guardar(recordatorios)
            estado = "activado" if r["activo"] else "pausado"
            return f"Recordatorio #{recordatorio_id} {estado}."

    return f"No se encontro el recordatorio #{recordatorio_id}."


def obtener_recordatorios_pendientes() -> list[dict]:
    """Devuelve los recordatorios que deben ejecutarse ahora."""
    recordatorios = _cargar()
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M")
    fecha_actual = ahora.strftime("%Y-%m-%d")
    dia_semana = ahora.weekday()  # 0=lun, 6=dom

    pendientes = []
    cambio = False

    for r in recordatorios:
        if not r["activo"]:
            continue
        if r["hora"] != hora_actual:
            continue
        if r["ultima_ejecucion"] == f"{fecha_actual} {hora_actual}":
            continue

        ejecutar = False

        if r["tipo"] == "diario":
            ejecutar = True
        elif r["tipo"] == "semanal" and r["dia_semana"] == dia_semana:
            ejecutar = True
        elif r["tipo"] == "unico" and r["fecha_unica"] == fecha_actual:
            ejecutar = True
        elif r["tipo"] == "cada_x_dias":
            if r["ultima_ejecucion"] is None:
                ejecutar = True
            else:
                ultima_fecha = datetime.strptime(
                    r["ultima_ejecucion"].split(" ")[0], "%Y-%m-%d"
                )
                dias_pasados = (ahora - ultima_fecha).days
                if dias_pasados >= r["dias_intervalo"]:
                    ejecutar = True

        if ejecutar:
            pendientes.append(r)
            r["ultima_ejecucion"] = f"{fecha_actual} {hora_actual}"
            cambio = True
            # Desactivar recordatorios unicos ya ejecutados
            if r["tipo"] == "unico":
                r["activo"] = False

    if cambio:
        _guardar(recordatorios)

    return pendientes
