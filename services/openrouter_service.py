from collections import defaultdict
from openai import AsyncOpenAI
from config.settings import settings

SYSTEM_PROMPT = (
    "Eres Syn, el asistente inteligente de Cortex. "
    "Ayudas con monitoreo, reportes, gestión de documentos, datos del sistema y asistencia general. "
    "Respondes claro, conciso y profesional. En español por defecto. "
    "Si no tienes info de algo del sistema, lo indicas honestamente."
)

MAX_HISTORY = 20


class OpenRouterService:
    """Servicio de integración con OpenRouter API usando formato OpenAI."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.histories: dict[str, list[dict]] = defaultdict(list)

    async def ask(self, message: str, user_id: str) -> str:
        history = self.histories[user_id]
        history.append({"role": "user", "content": message})

        # Mantener máximo MAX_HISTORY mensajes por usuario
        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        response = await self.client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=messages,
        )

        assistant_message = response.choices[0].message.content or "Sin respuesta."
        history.append({"role": "assistant", "content": assistant_message})

        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]

        return assistant_message


openrouter_service = OpenRouterService()
