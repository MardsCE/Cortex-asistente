import json
from collections import defaultdict
from openai import AsyncOpenAI
from config.settings import settings
from services.tools import TOOLS, ejecutar_herramienta, get_modo_citas
from services.drive_service import listar_registro
from services.memory_service import obtener_memorias_para_prompt

SYSTEM_PROMPT = (
    "Eres Syn, el asistente inteligente de Cortex. "
    "Siempre respondes en español.\n\n"
    "Ayudas con monitoreo, reportes, gestion de documentos, datos del sistema y asistencia general. "
    "Respondes claro, conciso y profesional.\n\n"
    "ARCHIVOS Y DRIVE:\n"
    "- Tienes herramientas para descargar archivos de Google Drive, registrarlos y gestionarlos.\n"
    "- Cuando el usuario te pase un link de Drive, usa descargar_drive y luego registrar_archivo.\n"
    "- Al registrar, SIEMPRE genera una descripcion AMPLIA y DETALLADA: que es el archivo, "
    "para que sirve, que contiene, contexto, tipo de datos, formato, y todo lo que ayude "
    "a entender el recurso sin abrirlo. Nada de descripciones cortas o vagas.\n"
    "- Si el usuario te dice que es el archivo o te da contexto, usalo para mejorar la descripcion.\n"
    "- Puedes listar, buscar, editar descripciones y eliminar archivos del registro.\n\n"
    "CITAS Y FUENTES:\n"
    "- SIEMPRE que respondas una pregunta usando informacion de un archivo registrado, "
    "DEBES indicar de que archivo sacaste la informacion. Ejemplo: '[Fuente: nombre_archivo]'\n"
    "- NUNCA respondas con informacion de archivos sin citar la fuente.\n"
    "- Antes de citar, usa leer_archivo para leer el contenido real. NO inventes.\n"
    "- Si no encuentras la informacion en ningun archivo, dilo claramente.\n\n"
    "MODO CITAS CON PRUEBA:\n"
    "- Si el modo de citas con prueba esta ACTIVO, ademas de citar la fuente, "
    "DEBES usar captura_prueba para generar una imagen del fragmento exacto que citas.\n"
    "- La captura debe mostrar el texto TAL CUAL aparece en el archivo.\n"
    "- Si el usuario dice 'activa citas', 'modo prueba', 'activa pruebas', "
    "o algo similar, usa toggle_modo_citas para activarlo.\n"
    "- Si dice 'desactiva citas' o similar, desactivalo.\n\n"
    "MEMORIAS:\n"
    "- Tienes un sistema de memorias persistentes. Las memorias se guardan en disco "
    "y sobreviven entre conversaciones. SIEMPRE las tienes disponibles.\n"
    "- Cuando el usuario te diga 'recuerda que...', 'no olvides...', 'toma nota...', "
    "o te de informacion importante sobre si mismo, su trabajo, preferencias, etc., "
    "USA guardar_memoria para guardarlo.\n"
    "- SE PROACTIVO: si detectas informacion valiosa (nombres, preferencias, datos de proyectos, "
    "decisiones importantes), guardala sin que te lo pidan.\n"
    "- SIEMPRE consulta tus memorias antes de responder para dar respuestas personalizadas "
    "y coherentes con lo que ya sabes del usuario.\n"
    "- Puedes eliminar memorias obsoletas o incorrectas cuando el usuario lo pida "
    "o cuando detectes que ya no aplican.\n"
    "- Usa categorias para organizar: preferencia, proyecto, dato, instruccion, "
    "contacto, recordatorio, general.\n\n"
    "Si no tienes info de algo del sistema, lo indicas honestamente."
)

MAX_HISTORY = 20
MAX_TOOL_CALLS = 8


class OpenRouterService:
    """Servicio de integracion con OpenRouter API con soporte de herramientas."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.histories: dict[str, list[dict]] = defaultdict(list)

    def _system_prompt(self, user_id: str) -> str:
        """Genera el system prompt incluyendo el registro y estado de citas."""
        registro = listar_registro()
        modo_citas = get_modo_citas(user_id)
        prompt = SYSTEM_PROMPT
        prompt += f"\n\nESTADO ACTUAL:"
        prompt += f"\n- user_id del usuario actual: {user_id}"
        prompt += f"\n- Modo citas con prueba: {'ACTIVO' if modo_citas else 'INACTIVO'}"
        if registro and "vacio" not in registro.lower():
            prompt += f"\n\nARCHIVOS REGISTRADOS ACTUALMENTE:\n{registro}"

        memorias = obtener_memorias_para_prompt()
        if memorias:
            prompt += f"\n\nMEMORIAS GUARDADAS (usa esta informacion para personalizar tus respuestas):\n{memorias}"

        return prompt

    def _recortar(self, history: list[dict]):
        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]

    async def ask(self, message: str, user_id: str) -> dict:
        """Procesa un mensaje. Retorna dict con 'texto' y opcionalmente 'imagenes'."""
        history = self.histories[user_id]
        history.append({"role": "user", "content": message})
        self._recortar(history)

        messages = [{"role": "system", "content": self._system_prompt(user_id)}] + history
        imagenes = []

        for _ in range(MAX_TOOL_CALLS):
            response = await self.client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=messages,
                tools=TOOLS,
            )

            choice = response.choices[0]

            if not choice.message.tool_calls:
                texto = choice.message.content or "Sin respuesta."
                history.append({"role": "assistant", "content": texto})
                self._recortar(history)
                return {"texto": texto, "imagenes": imagenes}

            # Procesar tool calls
            assistant_msg = {
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                resultado = ejecutar_herramienta(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": resultado,
                })

                # Si es captura_prueba, extraer ruta de imagen
                if tc.function.name == "captura_prueba":
                    try:
                        res = json.loads(resultado)
                        if res.get("estado") == "captura_generada":
                            imagenes.append(res["ruta_imagen"])
                    except (json.JSONDecodeError, KeyError):
                        pass

        # Agotaron intentos
        response = await self.client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=messages,
        )
        texto = response.choices[0].message.content or "Sin respuesta."
        history.append({"role": "assistant", "content": texto})
        self._recortar(history)
        return {"texto": texto, "imagenes": imagenes}


openrouter_service = OpenRouterService()
