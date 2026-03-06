import os
import re
import json
import gdown
import textwrap
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from services.json_store import cargar_json, guardar_json, obtener_lock, user_data_path
from services.timezone_utils import ahora


def _drive_dir(user_id: str) -> Path:
    return user_data_path(user_id, "drive")


def _registro_path(user_id: str) -> Path:
    return user_data_path(user_id, "registro.json")


def _capturas_dir(user_id: str) -> Path:
    return user_data_path(user_id, "capturas")


def _cargar_registro(user_id: str) -> list[dict]:
    return cargar_json(_registro_path(user_id))


def _guardar_registro(user_id: str, registro: list[dict]):
    guardar_json(_registro_path(user_id), registro)


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


def descargar_drive(user_id: str, url: str, nombre: str | None = None) -> dict:
    """Descarga un archivo o carpeta de Google Drive publico."""
    drive_dir = _drive_dir(user_id)
    drive_dir.mkdir(parents=True, exist_ok=True)

    drive_id = _extraer_id_drive(url)
    if not drive_id:
        return {"ok": False, "error": "No se pudo extraer el ID del link de Drive."}

    es_carpeta = "/folders/" in url

    try:
        if es_carpeta:
            nombre_sanitizado = re.sub(r'[^\w.-]', '_', nombre or drive_id)
            carpeta_destino = drive_dir / nombre_sanitizado
            carpeta_destino.mkdir(parents=True, exist_ok=True)
            gdown.download_folder(
                url=url, output=str(carpeta_destino), quiet=True
            )
            archivos = [f.name for f in carpeta_destino.rglob("*") if f.is_file()]
            ruta_local = str(carpeta_destino)
        else:
            archivo = gdown.download(id=drive_id, output=str(drive_dir) + "/", quiet=True)
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
    user_id: str, nombre: str, ruta: str, descripcion: str,
    url_drive: str, tipo: str, archivos: list[str],
) -> str:
    """Agrega una entrada al registro de archivos con su descripcion."""
    path = _registro_path(user_id)
    lock = obtener_lock(path)
    with lock:
        registro = cargar_json(path)
        for entrada in registro:
            if entrada.get("url_drive") == url_drive:
                entrada["descripcion"] = descripcion
                entrada["nombre"] = nombre
                guardar_json(path, registro)
                return f"Registro actualizado: {nombre}"

        registro.append({
            "nombre": nombre,
            "ruta": ruta,
            "descripcion": descripcion,
            "url_drive": url_drive,
            "tipo": tipo,
            "archivos": archivos,
        })
        guardar_json(path, registro)
    return f"Registrado: {nombre} ({len(archivos)} archivo(s))"


def listar_registro(user_id: str) -> str:
    """Devuelve el contenido del registro en texto legible."""
    registro = _cargar_registro(user_id)
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


def buscar_en_registro(user_id: str, termino: str) -> str:
    """Busca archivos en el registro por nombre o descripcion."""
    registro = _cargar_registro(user_id)
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


def editar_descripcion(user_id: str, nombre: str, nueva_descripcion: str) -> str:
    """Edita la descripcion de un archivo en el registro."""
    path = _registro_path(user_id)
    lock = obtener_lock(path)
    with lock:
        registro = cargar_json(path)
        for entrada in registro:
            if entrada["nombre"].lower() == nombre.lower():
                entrada["descripcion"] = nueva_descripcion
                guardar_json(path, registro)
                return f"Descripcion de '{nombre}' actualizada."
    return f"No se encontro '{nombre}' en el registro."


def eliminar_del_registro(user_id: str, nombre: str) -> str:
    """Elimina una entrada del registro (no borra los archivos)."""
    path = _registro_path(user_id)
    lock = obtener_lock(path)
    with lock:
        registro = cargar_json(path)
        nuevo = [e for e in registro if e["nombre"].lower() != nombre.lower()]
        if len(nuevo) == len(registro):
            return f"No se encontro '{nombre}' en el registro."
        guardar_json(path, nuevo)
    return f"'{nombre}' eliminado del registro."


def leer_archivo(user_id: str, nombre: str, max_lineas: int = 100) -> dict:
    """Lee el contenido de un archivo registrado para que el LLM pueda citarlo."""
    registro = _cargar_registro(user_id)

    entrada = None
    for e in registro:
        if e["nombre"].lower() == nombre.lower():
            entrada = e
            break

    if not entrada:
        return {"ok": False, "error": f"No se encontro '{nombre}' en el registro."}

    ruta = Path(entrada["ruta"])

    # Validar que la ruta este dentro del directorio del usuario
    try:
        ruta_resuelta = ruta.resolve()
        base_segura = _drive_dir(user_id).resolve()
        if not ruta_resuelta.is_relative_to(base_segura):
            return {"ok": False, "error": "Ruta de archivo no valida."}
    except (ValueError, OSError):
        return {"ok": False, "error": "Ruta de archivo no valida."}

    # Si es carpeta, listar archivos y leer los primeros
    if entrada["tipo"] == "carpeta":
        archivos_contenido = {}
        for archivo_nombre in entrada["archivos"][:5]:
            archivo_path = ruta / archivo_nombre
            if archivo_path.exists() and archivo_path.stat().st_size < 500_000:
                try:
                    contenido = archivo_path.read_text(encoding="utf-8", errors="replace")
                    lineas = contenido.splitlines()[:max_lineas]
                    archivos_contenido[archivo_nombre] = {
                        "contenido": "\n".join(lineas),
                        "total_lineas": len(contenido.splitlines()),
                        "truncado": len(contenido.splitlines()) > max_lineas,
                    }
                except Exception:
                    archivos_contenido[archivo_nombre] = {"contenido": "[No se pudo leer]"}
        return {
            "ok": True,
            "nombre": entrada["nombre"],
            "tipo": "carpeta",
            "archivos": archivos_contenido,
            "descripcion": entrada["descripcion"],
        }

    # Archivo individual
    if not ruta.exists():
        return {"ok": False, "error": f"El archivo no existe en disco: {ruta}"}

    extension = ruta.suffix.lower()
    if extension == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(ruta))
            total_pags = len(doc)
            paginas = []
            for i, pagina in enumerate(doc):
                if i >= 10:
                    break
                paginas.append(f"--- Pagina {i+1} ---\n{pagina.get_text()}")
            doc.close()
            return {
                "ok": True,
                "nombre": entrada["nombre"],
                "tipo": "pdf",
                "contenido": "\n\n".join(paginas),
                "total_paginas": total_pags,
                "descripcion": entrada["descripcion"],
            }
        except ImportError:
            return {"ok": False, "error": "PyMuPDF no instalado. No se puede leer PDFs."}
        except Exception as e:
            return {"ok": False, "error": f"Error al leer PDF: {e}"}

    # Archivos de texto
    try:
        contenido = ruta.read_text(encoding="utf-8", errors="replace")
        lineas = contenido.splitlines()
        return {
            "ok": True,
            "nombre": entrada["nombre"],
            "tipo": "texto",
            "contenido": "\n".join(lineas[:max_lineas]),
            "total_lineas": len(lineas),
            "truncado": len(lineas) > max_lineas,
            "descripcion": entrada["descripcion"],
        }
    except Exception as e:
        return {"ok": False, "error": f"Error al leer archivo: {e}"}


def _fuente():
    """Intenta cargar una fuente monoespaciada legible."""
    rutas_fuente = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]
    for ruta in rutas_fuente:
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, 16)
    return ImageFont.load_default()


def generar_captura(
    user_id: str,
    nombre_archivo: str,
    texto_cita: str,
    contexto: str = "",
) -> dict:
    """Genera una imagen/captura del texto citado de un archivo."""
    capturas_dir = _capturas_dir(user_id)
    capturas_dir.mkdir(parents=True, exist_ok=True)

    fuente = _fuente()
    fuente_titulo = _fuente()

    margen = 30
    ancho_max_chars = 80
    color_fondo = (30, 30, 35)
    color_texto = (220, 220, 220)
    color_titulo = (100, 180, 255)
    color_borde = (60, 60, 70)
    color_cita = (180, 255, 180)

    lineas = []
    lineas.append(f"ARCHIVO: {nombre_archivo}")
    lineas.append("=" * min(len(f"ARCHIVO: {nombre_archivo}"), ancho_max_chars))
    if contexto:
        lineas.append(f"Contexto: {contexto}")
        lineas.append("")

    lineas.append("CONTENIDO CITADO:")
    lineas.append("-" * 40)
    for linea_original in texto_cita.splitlines():
        wrapped = textwrap.wrap(linea_original, width=ancho_max_chars) or [""]
        lineas.extend(wrapped)
    lineas.append("-" * 40)
    lineas.append(f"Fuente: {nombre_archivo} | Captura generada por Syn")

    alto_linea = 22
    alto_total = margen * 2 + len(lineas) * alto_linea + 20
    ancho_total = margen * 2 + ancho_max_chars * 10

    img = Image.new("RGB", (ancho_total, alto_total), color_fondo)
    draw = ImageDraw.Draw(img)

    draw.rectangle(
        [5, 5, ancho_total - 6, alto_total - 6],
        outline=color_borde, width=2
    )

    y = margen
    for i, linea in enumerate(lineas):
        if i == 0:
            color = color_titulo
        elif linea.startswith("CONTENIDO CITADO"):
            color = color_cita
        elif linea.startswith("Fuente:"):
            color = color_titulo
        else:
            color = color_texto
        draw.text((margen, y), linea, fill=color, font=fuente)
        y += alto_linea

    # Nombre de archivo sanitizado + timestamp para evitar colisiones
    nombre_sanitizado = re.sub(r'[^\w.-]', '_', nombre_archivo)
    ts = ahora().strftime("%Y%m%d_%H%M%S_%f")
    nombre_img = f"cita_{nombre_sanitizado}_{ts}.png"
    ruta_img = capturas_dir / nombre_img
    img.save(str(ruta_img), "PNG")

    try:
        img_check = Image.open(str(ruta_img))
        w, h = img_check.size
        if w < 100 or h < 50:
            return {"ok": False, "error": "La captura generada es demasiado pequena."}
        img_check.close()
    except Exception as e:
        return {"ok": False, "error": f"Error verificando la captura: {e}"}

    return {
        "ok": True,
        "ruta_imagen": str(ruta_img),
        "nombre_archivo": nombre_archivo,
        "ancho": ancho_total,
        "alto": alto_total,
    }
