import json
from pathlib import Path

from services.timezone_utils import ahora

LOGS_DIR = Path("data/logs")


def _asegurar():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _archivo_hoy() -> Path:
    _asegurar()
    return LOGS_DIR / f"{ahora().strftime('%Y-%m-%d')}.log"


def _sanitizar(texto: str) -> str:
    """Elimina saltos de linea para prevenir log injection."""
    return texto.replace("\n", "\\n").replace("\r", "")


def _escribir(entrada: str):
    """Escribe una linea al log del dia actual."""
    archivo = _archivo_hoy()
    timestamp = ahora().strftime("%H:%M:%S")
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {entrada}\n")


def log_mensaje_usuario(user_id: str, mensaje: str):
    """Registra un mensaje entrante del usuario."""
    _escribir(f"MENSAJE | user={user_id} | {_sanitizar(mensaje[:200])}")


def log_respuesta(user_id: str, respuesta: str):
    """Registra la respuesta enviada al usuario."""
    _escribir(f"RESPUESTA | user={user_id} | {_sanitizar(respuesta[:200])}")


def log_tool_call(user_id: str, herramienta: str, argumentos: dict):
    """Registra cuando la IA llama una herramienta."""
    args_str = json.dumps(argumentos, ensure_ascii=False)
    if len(args_str) > 300:
        args_str = args_str[:300] + "..."
    _escribir(f"TOOL_CALL | user={user_id} | {herramienta} | args={_sanitizar(args_str)}")


def log_tool_result(user_id: str, herramienta: str, resultado: str):
    """Registra el resultado de una herramienta."""
    resultado_corto = resultado[:300] + "..." if len(resultado) > 300 else resultado
    _escribir(f"TOOL_RESULT | user={user_id} | {herramienta} | {_sanitizar(resultado_corto)}")


def log_error(user_id: str, contexto: str, error: str):
    """Registra un error."""
    _escribir(f"ERROR | user={user_id} | {contexto} | {_sanitizar(error)}")


def log_recordatorio(user_id: str, recordatorio_id: int, contenido: str):
    """Registra cuando se envia un recordatorio."""
    _escribir(f"RECORDATORIO | user={user_id} | #{recordatorio_id} | {_sanitizar(contenido[:200])}")


def log_sistema(mensaje: str):
    """Registra un evento del sistema (inicio, scheduler, etc)."""
    _escribir(f"SISTEMA | {_sanitizar(mensaje)}")


def obtener_log(fecha: str | None = None, user_id: str | None = None) -> str:
    """Lee el log de un dia especifico. Filtra por user_id si se proporciona."""
    _asegurar()
    if fecha is None:
        fecha = ahora().strftime("%Y-%m-%d")
    archivo = LOGS_DIR / f"{fecha}.log"
    if not archivo.exists():
        return f"No hay logs para el dia {fecha}."
    contenido = archivo.read_text(encoding="utf-8")
    if not contenido.strip():
        return f"El log del dia {fecha} esta vacio."

    # Filtrar por usuario: mostrar solo sus entradas + eventos del sistema
    if user_id:
        lineas = [
            l for l in contenido.splitlines()
            if f"user={user_id}" in l or "SISTEMA" in l
        ]
        if not lineas:
            return f"No hay actividad tuya registrada el dia {fecha}."
        contenido = "\n".join(lineas)

    return f"=== Log {fecha} ===\n{contenido}"


def listar_logs() -> str:
    """Lista los archivos de log disponibles."""
    _asegurar()
    archivos = sorted(LOGS_DIR.glob("*.log"), reverse=True)
    if not archivos:
        return "No hay logs disponibles."
    lineas = []
    for a in archivos[:30]:
        tamanio = a.stat().st_size
        lineas.append(f"- {a.stem} ({tamanio:,} bytes)")
    return "Logs disponibles:\n" + "\n".join(lineas)
