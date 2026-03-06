import json
from pathlib import Path
from datetime import datetime

LOGS_DIR = Path("data/logs")


def _asegurar():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _archivo_hoy() -> Path:
    _asegurar()
    return LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"


def _escribir(entrada: str):
    """Escribe una linea al log del dia actual."""
    archivo = _archivo_hoy()
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {entrada}\n")


def log_mensaje_usuario(user_id: str, mensaje: str):
    """Registra un mensaje entrante del usuario."""
    _escribir(f"MENSAJE | user={user_id} | {mensaje[:200]}")


def log_respuesta(user_id: str, respuesta: str):
    """Registra la respuesta enviada al usuario."""
    _escribir(f"RESPUESTA | user={user_id} | {respuesta[:200]}")


def log_tool_call(user_id: str, herramienta: str, argumentos: dict):
    """Registra cuando la IA llama una herramienta."""
    args_str = json.dumps(argumentos, ensure_ascii=False)
    if len(args_str) > 300:
        args_str = args_str[:300] + "..."
    _escribir(f"TOOL_CALL | user={user_id} | {herramienta} | args={args_str}")


def log_tool_result(user_id: str, herramienta: str, resultado: str):
    """Registra el resultado de una herramienta."""
    resultado_corto = resultado[:300] + "..." if len(resultado) > 300 else resultado
    _escribir(f"TOOL_RESULT | user={user_id} | {herramienta} | {resultado_corto}")


def log_error(user_id: str, contexto: str, error: str):
    """Registra un error."""
    _escribir(f"ERROR | user={user_id} | {contexto} | {error}")


def log_recordatorio(user_id: str, recordatorio_id: int, contenido: str):
    """Registra cuando se envia un recordatorio."""
    _escribir(f"RECORDATORIO | user={user_id} | #{recordatorio_id} | {contenido[:200]}")


def log_sistema(mensaje: str):
    """Registra un evento del sistema (inicio, scheduler, etc)."""
    _escribir(f"SISTEMA | {mensaje}")


def obtener_log(fecha: str | None = None) -> str:
    """Lee el log de un dia especifico o del dia actual."""
    _asegurar()
    if fecha is None:
        fecha = datetime.now().strftime("%Y-%m-%d")
    archivo = LOGS_DIR / f"{fecha}.log"
    if not archivo.exists():
        return f"No hay logs para el dia {fecha}."
    contenido = archivo.read_text(encoding="utf-8")
    if not contenido.strip():
        return f"El log del dia {fecha} esta vacio."
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
