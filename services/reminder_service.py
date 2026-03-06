import re
from pathlib import Path
from datetime import datetime

from services.json_store import cargar_json, guardar_json, obtener_lock
from services.timezone_utils import ahora

REMINDERS_PATH = Path("data/recordatorios.json")


def _siguiente_id(recordatorios: list[dict]) -> int:
    if not recordatorios:
        return 1
    return max(r["id"] for r in recordatorios) + 1


def _normalizar_hora(hora: str) -> str | None:
    """Normaliza hora a formato HH:MM. Retorna None si es invalida."""
    hora = hora.strip()
    match = re.match(r'^(\d{1,2}):(\d{2})$', hora)
    if not match:
        return None
    h, m = int(match.group(1)), int(match.group(2))
    if h > 23 or m > 59:
        return None
    return f"{h:02d}:{m:02d}"


def _validar_fecha(fecha: str) -> bool:
    """Valida que sea formato YYYY-MM-DD valido."""
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except ValueError:
        return False


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
    # Validaciones estrictas
    if not contenido or not contenido.strip():
        return "ERROR: Falta el contenido del recordatorio. Pregunta al usuario que quiere recordar."
    if not hora or not hora.strip():
        return "ERROR: Falta la hora. Pregunta al usuario a que hora quiere el recordatorio (formato HH:MM, 24h)."
    if tipo not in ("unico", "diario", "semanal", "cada_x_dias"):
        return f"ERROR: Tipo '{tipo}' no valido. Debe ser: unico, diario, semanal o cada_x_dias."

    # Normalizar y validar hora
    hora_normalizada = _normalizar_hora(hora)
    if hora_normalizada is None:
        return f"ERROR: Hora '{hora}' no valida. Usa formato HH:MM (24h), ejemplo: 09:00, 14:30."

    if tipo == "unico":
        if not fecha_unica:
            return "ERROR: Para recordatorio unico falta la fecha (YYYY-MM-DD). Pregunta al usuario."
        if not _validar_fecha(fecha_unica):
            return f"ERROR: Fecha '{fecha_unica}' no valida. Usa formato YYYY-MM-DD, ejemplo: 2026-03-15."
        # No permitir fechas pasadas
        hoy = ahora().strftime("%Y-%m-%d")
        if fecha_unica < hoy:
            return f"ERROR: La fecha {fecha_unica} ya paso. Pide una fecha futura."

    if tipo == "semanal":
        if dia_semana is None:
            return "ERROR: Para recordatorio semanal falta el dia de la semana (0=lunes a 6=domingo). Pregunta al usuario."
        if not isinstance(dia_semana, int) or dia_semana < 0 or dia_semana > 6:
            return f"ERROR: Dia de la semana '{dia_semana}' no valido. Debe ser 0 (lunes) a 6 (domingo)."

    if tipo == "cada_x_dias":
        if not dias_intervalo:
            return "ERROR: Para recordatorio cada X dias falta el intervalo. Pregunta al usuario cada cuantos dias."
        if not isinstance(dias_intervalo, int) or dias_intervalo < 1:
            return f"ERROR: Intervalo '{dias_intervalo}' no valido. Debe ser un numero positivo."

    lock = obtener_lock(REMINDERS_PATH)
    with lock:
        recordatorios = cargar_json(REMINDERS_PATH)
        momento = ahora()
        nuevo = {
            "id": _siguiente_id(recordatorios),
            "user_id": user_id,
            "chat_id": chat_id,
            "contenido": contenido,
            "tipo": tipo,
            "hora": hora_normalizada,
            "dia_semana": dia_semana,
            "dias_intervalo": dias_intervalo,
            "fecha_unica": fecha_unica,
            "activo": True,
            "fecha_creacion": momento.strftime("%Y-%m-%d %H:%M"),
            # Para cada_x_dias, iniciar desde ahora para que el primer disparo sea despues del intervalo
            "ultima_ejecucion": momento.strftime("%Y-%m-%d %H:%M") if tipo == "cada_x_dias" else None,
        }
        recordatorios.append(nuevo)
        guardar_json(REMINDERS_PATH, recordatorios)

    desc_tipo = {
        "unico": f"una vez el {fecha_unica}",
        "diario": "todos los dias",
        "semanal": f"cada semana (dia {dia_semana})",
        "cada_x_dias": f"cada {dias_intervalo} dias",
    }
    return (
        f"Recordatorio #{nuevo['id']} creado: {contenido}\n"
        f"Frecuencia: {desc_tipo.get(tipo, tipo)} a las {hora_normalizada}"
    )


def listar_recordatorios(user_id: str) -> str:
    """Lista los recordatorios de un usuario."""
    recordatorios = cargar_json(REMINDERS_PATH)
    del_usuario = [r for r in recordatorios if r["user_id"] == user_id]

    if not del_usuario:
        return "No tienes recordatorios configurados."

    lineas = []
    for r in del_usuario:
        estado = "Activo" if r["activo"] else "Pausado"
        tipo_desc = r["tipo"]
        if r["tipo"] == "semanal":
            dias = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
            idx = r.get("dia_semana", 0)
            tipo_desc = f"semanal ({dias[idx] if 0 <= idx <= 6 else '?'})"
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
    lock = obtener_lock(REMINDERS_PATH)
    with lock:
        recordatorios = cargar_json(REMINDERS_PATH)
        original = len(recordatorios)
        recordatorios = [
            r for r in recordatorios
            if not (r["id"] == recordatorio_id and r["user_id"] == user_id)
        ]
        if len(recordatorios) == original:
            return f"No se encontro el recordatorio #{recordatorio_id}."
        guardar_json(REMINDERS_PATH, recordatorios)
    return f"Recordatorio #{recordatorio_id} eliminado."


def toggle_recordatorio(user_id: str, recordatorio_id: int) -> str:
    """Activa o pausa un recordatorio."""
    lock = obtener_lock(REMINDERS_PATH)
    with lock:
        recordatorios = cargar_json(REMINDERS_PATH)
        for r in recordatorios:
            if r["id"] == recordatorio_id and r["user_id"] == user_id:
                r["activo"] = not r["activo"]
                guardar_json(REMINDERS_PATH, recordatorios)
                estado = "activado" if r["activo"] else "pausado"
                return f"Recordatorio #{recordatorio_id} {estado}."
    return f"No se encontro el recordatorio #{recordatorio_id}."


def obtener_recordatorios_pendientes() -> list[dict]:
    """Devuelve los recordatorios que deben ejecutarse ahora."""
    lock = obtener_lock(REMINDERS_PATH)
    with lock:
        recordatorios = cargar_json(REMINDERS_PATH)
        momento = ahora()
        hora_actual = momento.strftime("%H:%M")
        fecha_actual = momento.strftime("%Y-%m-%d")
        dia_semana = momento.weekday()

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
            elif r["tipo"] == "semanal" and r.get("dia_semana") == dia_semana:
                ejecutar = True
            elif r["tipo"] == "unico":
                if r.get("fecha_unica") == fecha_actual:
                    ejecutar = True
                elif r.get("fecha_unica", "") < fecha_actual:
                    # Fecha pasada, desactivar
                    r["activo"] = False
                    cambio = True
            elif r["tipo"] == "cada_x_dias":
                if r["ultima_ejecucion"] is None:
                    ejecutar = True
                else:
                    try:
                        ultima_fecha = datetime.strptime(
                            r["ultima_ejecucion"].split(" ")[0], "%Y-%m-%d"
                        )
                        dias_pasados = (momento.replace(tzinfo=None) - ultima_fecha).days
                        if dias_pasados >= r.get("dias_intervalo", 1):
                            ejecutar = True
                    except (ValueError, TypeError):
                        ejecutar = True

            if ejecutar:
                pendientes.append(r)
                r["ultima_ejecucion"] = f"{fecha_actual} {hora_actual}"
                cambio = True
                if r["tipo"] == "unico":
                    r["activo"] = False

        if cambio:
            guardar_json(REMINDERS_PATH, recordatorios)

    return pendientes
