import os
import re
import json
import gdown
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DRIVE_DIR = Path("data/drive")
REGISTRO_PATH = Path("data/registro.json")
CAPTURAS_DIR = Path("data/capturas")


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


def leer_archivo(nombre: str, max_lineas: int = 100) -> dict:
    """Lee el contenido de un archivo registrado para que el LLM pueda citarlo."""
    registro = _cargar_registro()

    entrada = None
    for e in registro:
        if e["nombre"].lower() == nombre.lower():
            entrada = e
            break

    if not entrada:
        return {"ok": False, "error": f"No se encontro '{nombre}' en el registro."}

    ruta = Path(entrada["ruta"])

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
                "total_paginas": len(doc) if hasattr(doc, '__len__') else "desconocido",
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
    nombre_archivo: str,
    texto_cita: str,
    contexto: str = "",
) -> dict:
    """Genera una imagen/captura del texto citado de un archivo.

    Renderiza el texto en una imagen limpia y legible que sirve como prueba
    de la fuente de la informacion.
    """
    CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)

    fuente = _fuente()
    fuente_titulo = _fuente()

    # Configuracion de la imagen
    margen = 30
    ancho_max_chars = 80
    color_fondo = (30, 30, 35)
    color_texto = (220, 220, 220)
    color_titulo = (100, 180, 255)
    color_borde = (60, 60, 70)
    color_cita = (180, 255, 180)

    # Preparar texto
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

    # Calcular tamano
    alto_linea = 22
    alto_total = margen * 2 + len(lineas) * alto_linea + 20
    ancho_total = margen * 2 + ancho_max_chars * 10

    # Crear imagen
    img = Image.new("RGB", (ancho_total, alto_total), color_fondo)
    draw = ImageDraw.Draw(img)

    # Borde
    draw.rectangle(
        [5, 5, ancho_total - 6, alto_total - 6],
        outline=color_borde, width=2
    )

    # Dibujar texto
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

    # Guardar
    nombre_img = f"cita_{nombre_archivo.replace(' ', '_')}_{os.getpid()}.png"
    ruta_img = CAPTURAS_DIR / nombre_img
    img.save(str(ruta_img), "PNG")

    # Verificar que la imagen se genero bien
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
