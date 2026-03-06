import json
from services import drive_service, memory_service, web_search_service

# Estado del modo citas por usuario: {user_id: bool}
_modo_citas: dict[str, bool] = {}


def get_modo_citas(user_id: str) -> bool:
    return _modo_citas.get(user_id, False)


def set_modo_citas(user_id: str, activo: bool):
    _modo_citas[user_id] = activo


# Definicion de herramientas que el LLM puede usar
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "descargar_drive",
            "description": (
                "Descarga un archivo o carpeta publica de Google Drive y lo guarda localmente. "
                "Usa esta herramienta cuando el usuario comparta un link de Google Drive."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Link de Google Drive (archivo o carpeta publica)",
                    },
                    "nombre": {
                        "type": "string",
                        "description": "Nombre corto para identificar este recurso en el registro",
                    },
                },
                "required": ["url", "nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_archivo",
            "description": (
                "Registra un archivo descargado en el directorio con su descripcion detallada. "
                "Usa esta herramienta SIEMPRE despues de descargar algo de Drive para guardar "
                "la descripcion que explica que contiene el archivo, para que sirve, "
                "que tipo de contenido tiene, y cualquier dato relevante."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre del recurso",
                    },
                    "ruta": {
                        "type": "string",
                        "description": "Ruta local donde se guardo",
                    },
                    "descripcion": {
                        "type": "string",
                        "description": (
                            "Descripcion AMPLIA y DETALLADA del contenido. "
                            "Debe explicar: que es, para que sirve, que tipo de archivos contiene, "
                            "contexto de uso, y cualquier informacion util para entender el recurso "
                            "sin necesidad de abrirlo."
                        ),
                    },
                    "url_drive": {
                        "type": "string",
                        "description": "Link original de Google Drive",
                    },
                    "tipo": {
                        "type": "string",
                        "enum": ["archivo", "carpeta"],
                        "description": "Si es archivo individual o carpeta",
                    },
                    "archivos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de nombres de archivos descargados",
                    },
                },
                "required": ["nombre", "ruta", "descripcion", "url_drive", "tipo", "archivos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_archivos",
            "description": (
                "Lista todos los archivos y carpetas registrados con sus descripciones. "
                "Usa esta herramienta cuando el usuario pregunte que archivos hay guardados."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_archivo",
            "description": (
                "Busca archivos en el registro por nombre, descripcion o contenido. "
                "Usa esta herramienta cuando el usuario busque algo especifico entre los archivos guardados."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "termino": {
                        "type": "string",
                        "description": "Texto a buscar en nombres y descripciones",
                    },
                },
                "required": ["termino"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "editar_descripcion",
            "description": (
                "Edita o corrige la descripcion de un archivo registrado. "
                "Usa esta herramienta cuando el usuario pida cambiar, corregir o ampliar "
                "la descripcion de un archivo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre del archivo en el registro",
                    },
                    "nueva_descripcion": {
                        "type": "string",
                        "description": (
                            "Nueva descripcion AMPLIA y DETALLADA. "
                            "Debe ser clara, sin ambiguedades, y explicar bien el contenido."
                        ),
                    },
                },
                "required": ["nombre", "nueva_descripcion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_archivo",
            "description": (
                "Elimina un archivo del registro. "
                "Usa esta herramienta cuando el usuario pida quitar un archivo del directorio."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre del archivo a eliminar del registro",
                    },
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "leer_archivo",
            "description": (
                "Lee el contenido real de un archivo registrado para poder citarlo correctamente. "
                "SIEMPRE usa esta herramienta antes de responder preguntas sobre el contenido "
                "de un archivo. Nunca inventes informacion sin leer primero."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre del archivo en el registro",
                    },
                    "max_lineas": {
                        "type": "integer",
                        "description": "Maximo de lineas a leer (default 100)",
                    },
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "captura_prueba",
            "description": (
                "Genera una imagen/captura del fragmento de texto citado como prueba visual. "
                "Usa esta herramienta SOLO cuando el modo de citas con prueba este activo. "
                "Genera una imagen con el texto exacto del archivo que se esta citando, "
                "con el nombre del archivo fuente visible. La imagen se envia al usuario como foto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_archivo": {
                        "type": "string",
                        "description": "Nombre del archivo del que se extrae la cita",
                    },
                    "texto_cita": {
                        "type": "string",
                        "description": (
                            "El fragmento EXACTO de texto que se esta citando. "
                            "Debe ser el texto tal cual aparece en el archivo, sin modificar."
                        ),
                    },
                    "contexto": {
                        "type": "string",
                        "description": "Breve nota sobre que se busco o por que se cita esto",
                    },
                },
                "required": ["nombre_archivo", "texto_cita"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_memoria",
            "description": (
                "Guarda una memoria o nota importante para recordar en el futuro. "
                "Usa esta herramienta cuando el usuario te diga algo que quiere que recuerdes, "
                "o cuando TU detectes informacion importante que vale la pena memorizar: "
                "preferencias del usuario, datos clave, instrucciones recurrentes, contexto de proyectos, "
                "nombres, fechas importantes, decisiones tomadas, etc. "
                "SE INTELIGENTE: si el usuario dice 'recuerda que...', 'no olvides que...', "
                "'toma nota de...', o te da informacion relevante sobre si mismo o su trabajo, guardala. "
                "Tambien puedes guardar memorias por iniciativa propia si detectas algo util."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contenido": {
                        "type": "string",
                        "description": (
                            "El contenido de la memoria. Escribe de forma clara y concisa "
                            "pero con suficiente detalle para que sea util en el futuro. "
                            "Ejemplo: 'El usuario prefiere respuestas cortas y directas' o "
                            "'El proyecto Alpha usa Python 3.11 y FastAPI'"
                        ),
                    },
                    "categoria": {
                        "type": "string",
                        "description": (
                            "Categoria para organizar la memoria. Usa categorias como: "
                            "preferencia, proyecto, dato, instruccion, contacto, recordatorio, general"
                        ),
                    },
                },
                "required": ["contenido", "categoria"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_memorias",
            "description": (
                "Lista todas las memorias guardadas o las de una categoria especifica. "
                "Usa esta herramienta cuando el usuario pregunte que recuerdas, "
                "que memorias hay, o pida ver sus notas guardadas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Filtrar por categoria (opcional). Dejar vacio para ver todas.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_memoria",
            "description": (
                "Elimina una memoria por su numero de ID. "
                "Usa esta herramienta cuando el usuario pida borrar o quitar una memoria especifica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memoria_id": {
                        "type": "integer",
                        "description": "El numero ID de la memoria a eliminar",
                    },
                },
                "required": ["memoria_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_memoria",
            "description": (
                "Busca memorias por contenido o categoria. "
                "Usa esta herramienta cuando necesites encontrar algo especifico entre las memorias."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "termino": {
                        "type": "string",
                        "description": "Texto a buscar en las memorias",
                    },
                },
                "required": ["termino"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": (
                "Busca informacion en internet. Usa esta herramienta cuando: "
                "1) El usuario pregunte algo que no esta en los archivos guardados ni en las memorias. "
                "2) El usuario pida explicitamente buscar en internet. "
                "3) Se necesite informacion actualizada (noticias, precios, eventos, etc.). "
                "4) No tengas suficiente informacion para responder con certeza. "
                "SIEMPRE indica al usuario que la informacion viene de una busqueda web."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": (
                            "La consulta de busqueda. Escribe una busqueda clara y especifica. "
                            "Puedes escribir en español o ingles segun convenga para mejores resultados."
                        ),
                    },
                    "max_resultados": {
                        "type": "integer",
                        "description": "Cantidad maxima de resultados (default 5, max 10)",
                    },
                },
                "required": ["consulta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_noticias",
            "description": (
                "Busca noticias recientes en internet. Usa esta herramienta cuando el usuario "
                "pregunte por noticias, eventos recientes, o informacion de actualidad."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Tema o consulta para buscar noticias",
                    },
                    "max_resultados": {
                        "type": "integer",
                        "description": "Cantidad maxima de resultados (default 5, max 10)",
                    },
                },
                "required": ["consulta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_modo_citas",
            "description": (
                "Activa o desactiva el modo de citas con prueba para el usuario. "
                "Cuando esta activo, cada vez que se cite informacion de un archivo "
                "se genera una captura/imagen como prueba visual."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "ID del usuario",
                    },
                    "activar": {
                        "type": "boolean",
                        "description": "True para activar, False para desactivar",
                    },
                },
                "required": ["user_id", "activar"],
            },
        },
    },
]


def ejecutar_herramienta(nombre: str, argumentos: dict) -> str:
    """Ejecuta una herramienta por nombre y devuelve el resultado como texto."""
    if nombre == "descargar_drive":
        resultado = drive_service.descargar_drive(argumentos["url"], argumentos.get("nombre"))
        if resultado["ok"]:
            return json.dumps({
                "estado": "descargado",
                "ruta": resultado["ruta"],
                "archivos": resultado["archivos"],
                "tipo": resultado["tipo"],
                "nota": "Ahora usa registrar_archivo para guardar este recurso con una descripcion detallada.",
            }, ensure_ascii=False)
        return json.dumps({"estado": "error", "error": resultado["error"]}, ensure_ascii=False)

    elif nombre == "registrar_archivo":
        return drive_service.agregar_al_registro(
            argumentos["nombre"],
            argumentos["ruta"],
            argumentos["descripcion"],
            argumentos["url_drive"],
            argumentos["tipo"],
            argumentos["archivos"],
        )

    elif nombre == "listar_archivos":
        return drive_service.listar_registro()

    elif nombre == "buscar_archivo":
        return drive_service.buscar_en_registro(argumentos["termino"])

    elif nombre == "editar_descripcion":
        return drive_service.editar_descripcion(
            argumentos["nombre"], argumentos["nueva_descripcion"]
        )

    elif nombre == "eliminar_archivo":
        return drive_service.eliminar_del_registro(argumentos["nombre"])

    elif nombre == "leer_archivo":
        resultado = drive_service.leer_archivo(
            argumentos["nombre"], argumentos.get("max_lineas", 100)
        )
        return json.dumps(resultado, ensure_ascii=False)

    elif nombre == "captura_prueba":
        resultado = drive_service.generar_captura(
            argumentos["nombre_archivo"],
            argumentos["texto_cita"],
            argumentos.get("contexto", ""),
        )
        if resultado["ok"]:
            return json.dumps({
                "estado": "captura_generada",
                "ruta_imagen": resultado["ruta_imagen"],
                "nota": "La imagen sera enviada automaticamente al usuario.",
            }, ensure_ascii=False)
        return json.dumps({"estado": "error", "error": resultado["error"]}, ensure_ascii=False)

    elif nombre == "guardar_memoria":
        return memory_service.agregar_memoria(
            argumentos["contenido"], argumentos.get("categoria", "general")
        )

    elif nombre == "listar_memorias":
        return memory_service.listar_memorias(argumentos.get("categoria"))

    elif nombre == "eliminar_memoria":
        return memory_service.eliminar_memoria(argumentos["memoria_id"])

    elif nombre == "buscar_memoria":
        return memory_service.buscar_memorias(argumentos["termino"])

    elif nombre == "buscar_web":
        max_res = min(argumentos.get("max_resultados", 5), 10)
        return web_search_service.buscar_web(argumentos["consulta"], max_res)

    elif nombre == "buscar_noticias":
        max_res = min(argumentos.get("max_resultados", 5), 10)
        return web_search_service.buscar_noticias(argumentos["consulta"], max_res)

    elif nombre == "toggle_modo_citas":
        activar = argumentos["activar"]
        user_id = argumentos["user_id"]
        set_modo_citas(user_id, activar)
        estado = "activado" if activar else "desactivado"
        return f"Modo de citas con prueba {estado} para este usuario."

    return f"Herramienta '{nombre}' no reconocida."
