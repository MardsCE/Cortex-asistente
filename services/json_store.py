import json
import threading
import tempfile
from pathlib import Path

_locks: dict[str, threading.Lock] = {}
_meta_lock = threading.Lock()


def obtener_lock(path: Path) -> threading.Lock:
    """Devuelve un Lock por archivo para operaciones read-modify-write."""
    key = str(path)
    with _meta_lock:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def cargar_json(path: Path) -> list[dict]:
    """Lee un archivo JSON. Devuelve lista vacia si no existe o esta corrupto."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []


def guardar_json(path: Path, data: list[dict]):
    """Escribe un archivo JSON de forma atomica (temp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            f.write(contenido)
        Path(tmp_path).replace(path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def user_data_path(user_id: str, filename: str) -> Path:
    """Devuelve ruta de datos aislada por usuario: data/users/{user_id}/{filename}"""
    return Path("data/users") / user_id / filename
