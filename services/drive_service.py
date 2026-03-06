import os
import re
import json
import gdown
from pathlib import Path

DRIVE_DIR = Path("data/drive")
REGISTRO_PATH = Path("data/registro.json")


def _asegurar_dirs():
    DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRO_PATH.exists():
        REGISTRO_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRO_PATH.write_text("[]", encoding="utf-8")


def _cargar_registro() -> list[dict]:
    _asegurar_dirs()
    return json.loads(REGISTRO_PATH.read_text(encoding="utf-8"))


def _guardar_registro(registro: list[dict]):
    _asegurar_dirs()
    REGISTRO_PATH.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _extraer_id_drive(url: str) -> str | None:
    """Extrae el ID de archivo o carpeta de un link de Google Drive."""
    patrones = [
        r"/folders/([a-zA-Z0-9_-]+)",
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
    ]
    for patron in patrones:
        match = re.search(patron, url)
        if match:
            return match.group(1)
    return None


def descargar_drive(url: str, nombre: str | None = None) -> dict:
    """Descarga un archivo o carpeta de Google Drive publico."""
    _asegurar_dirs()

    drive_id = _extraer_id_drive(url)
    if not drive_id:
        return {"ok": False, "error": "No se pudo extraer el ID del link de Drive."}

    destino = str(DRIVE_DIR)

    es_carpeta = "/folders/" in url

    try:
        if es_carpeta:
            carpeta_destino = DRIVE_DIR / (nombre or drive_id)
            carpeta_destino.mkdir(parents=True, exist_ok=True)
            gdown.download_folder(
                url=url, output=str(carpeta_destino), quiet=True
            )
            archivos = [f.name for f in carpeta_destino.rglob("*") if f.is_file()]
            ruta_local = str(carpeta_destino)
        else:
            archivo = gdown.download(id=drive_id, output=destino + "/", quiet=True)
            if not archivo:
                return {"ok": False, "error": "No se pudo descargar el archivo. Verifica que el link sea publico."}
            archivos = [os.path.basename(archivo)]
            ruta_local = archivo
    except Exception as e:
        return {"ok": False, "error": f"Error al descargar: {e}"}

    return {
        "ok": True,
        "ruta": ruta_local,
        "archivos": archivos,
        "tipo": "carpeta" if es_carpeta else "archivo",
        "drive_id": drive_id,
    }


def agregar_al_registro(
    nombre: str, ruta: str, descripcion: str, url_drive: str, tipo: str, archivos: list[str]
) -> str:
    """Agrega una entrada al registro de archivos con su descripcion."""
    registro = _cargar_registro()

    # Verificar si ya existe
    for entrada in registro:
        if entrada.get("url_drive") == url_drive:
            entrada["descripcion"] = descripcion
            entrada["nombre"] = nombre
            _guardar_registro(registro)
            return f"Registro actualizado: {nombre}"

    registro.append({
        "nombre": nombre,
        "ruta": ruta,
        "descripcion": descripcion,
        "url_drive": url_drive,
        "tipo": tipo,
        "archivos": archivos,
    })
    _guardar_registro(registro)
    return f"Registrado: {nombre} ({len(archivos)} archivo(s))"


def listar_registro() -> str:
    """Devuelve el contenido del registro en texto legible."""
    registro = _cargar_registro()
    if not registro:
        return "El registro esta vacio. No hay archivos guardados."

    lineas = []
    for i, entrada in enumerate(registro, 1):
        lineas.append(
            f"{i}. {entrada['nombre']} [{entrada['tipo']}]\n"
            f"   Descripcion: {entrada['descripcion']}\n"
            f"   Archivos: {', '.join(entrada['archivos'][:10])}"
            f"{'...' if len(entrada['archivos']) > 10 else ''}\n"
            f"   Ruta: {entrada['ruta']}"
        )
    return "\n\n".join(lineas)


def buscar_en_registro(termino: str) -> str:
    """Busca archivos en el registro por nombre o descripcion."""
    registro = _cargar_registro()
    termino_lower = termino.lower()
    resultados = []

    for entrada in registro:
        if (
            termino_lower in entrada["nombre"].lower()
            or termino_lower in entrada["descripcion"].lower()
            or any(termino_lower in a.lower() for a in entrada["archivos"])
        ):
            resultados.append(
                f"- {entrada['nombre']}: {entrada['descripcion'][:200]}"
            )

    if not resultados:
        return f"No se encontraron archivos relacionados con '{termino}'."
    return "Resultados:\n" + "\n".join(resultados)


def editar_descripcion(nombre: str, nueva_descripcion: str) -> str:
    """Edita la descripcion de un archivo en el registro."""
    registro = _cargar_registro()

    for entrada in registro:
        if entrada["nombre"].lower() == nombre.lower():
            entrada["descripcion"] = nueva_descripcion
            _guardar_registro(registro)
            return f"Descripcion de '{nombre}' actualizada."

    return f"No se encontro '{nombre}' en el registro."


def eliminar_del_registro(nombre: str) -> str:
    """Elimina una entrada del registro (no borra los archivos)."""
    registro = _cargar_registro()
    nuevo = [e for e in registro if e["nombre"].lower() != nombre.lower()]

    if len(nuevo) == len(registro):
        return f"No se encontro '{nombre}' en el registro."

    _guardar_registro(nuevo)
    return f"'{nombre}' eliminado del registro."
