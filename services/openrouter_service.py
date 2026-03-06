import json
from collections import defaultdict
from openai import AsyncOpenAI
from config.settings import settings
from services.tools import TOOLS, ejecutar_herramienta
from services.drive_service import listar_registro

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
    "Si no tienes info de algo del sistema, lo indicas honestamente."
)

MAX_HISTORY = 20
MAX_TOOL_CALLS = 5


class OpenRouterService:
    """Servicio de integracion con OpenRouter API con soporte de herramientas."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.histories: dict[str, list[dict]] = defaultdict(list)

    def _system_prompt(self) -> str:
        """Genera el system prompt incluyendo el registro actual de archivos."""
        registro = listar_registro()
        prompt = SYSTEM_PROMPT
        if registro and "vacio" not in registro.lower():
            prompt += f"\n\nARCHIVOS REGISTRADOS ACTUALMENTE:\n{registro}"
        return prompt

    def _recortar(self, history: list[dict]):
        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]

    async def ask(self, message: str, user_id: str) -> str:
        history = self.histories[user_id]
        history.append({"role": "user", "content": message})
        self._recortar(history)

        messages = [{"role": "system", "content": self._system_prompt()}] + history

        for _ in range(MAX_TOOL_CALLS):
            response = await self.client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=messages,
                tools=TOOLS,
            )

            choice = response.choices[0]

            # Si no hay tool calls, devolver la respuesta directa
            if not choice.message.tool_calls:
                texto = choice.message.content or "Sin respuesta."
                history.append({"role": "assistant", "content": texto})
                self._recortar(history)
                return texto

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

        # Si se agotaron los intentos, pedir respuesta final sin tools
        response = await self.client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=messages,
        )
        texto = response.choices[0].message.content or "Sin respuesta."
        history.append({"role": "assistant", "content": texto})
        self._recortar(history)
        return texto


openrouter_service = OpenRouterService()
