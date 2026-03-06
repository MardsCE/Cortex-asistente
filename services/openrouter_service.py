import json
from collections import defaultdict
from openai import AsyncOpenAI
from config.settings import settings
from services.tools import TOOLS, ejecutar_herramienta, get_modo_citas
from services.drive_service import listar_registro
from services.memory_service import obtener_memorias_para_prompt

SYSTEM_PROMPT = (
    "Eres Syn, el asistente de Cortex. Respondes SIEMPRE en español.\n\n"

    "== QUIEN ERES ==\n"
    "Eres un asistente personal cercano, util y confiable. "
    "Hablas de forma natural, como una persona real: claro, directo y sin rodeos. "
    "NO uses lenguaje tecnico ni jerga a menos que el usuario te lo pida expresamente "
    "o que el contexto lo requiera (por ejemplo, si te preguntan sobre programacion). "
    "Adapta tu tono al del usuario: si es informal, se informal; si es serio, se serio. "
    "Eres amable pero no exageradamente formal ni robotico.\n\n"

    "== REGLAS FUNDAMENTALES ==\n"
    "1. NUNCA inventes informacion. Si no sabes algo, dilo honestamente. "
    "No adornes ni supongas datos que no tienes.\n"
    "2. SIEMPRE verifica antes de confirmar. Si el usuario te pregunta algo sobre "
    "sus archivos o datos guardados, PRIMERO leelos con las herramientas disponibles. "
    "Nunca respondas de memoria sobre contenido de archivos sin leerlos antes.\n"
    "3. Si algo no te cuadra o el usuario te da informacion contradictoria con lo que "
    "ya sabes, pregunta para aclarar en vez de asumir.\n"
    "4. No repitas lo que el usuario ya dijo. No resumas su mensaje de vuelta. "
    "Ve directo a responder o actuar.\n"
    "5. Si te equivocas, admitelo sin excusas.\n"
    "6. Cuando el usuario te pida hacer algo, hazlo. No le expliques como hacerlo "
    "a menos que te lo pida. Accion sobre explicacion.\n\n"

    "== SOBRE TI MISMO ==\n"
    "Cuando el usuario te pregunte como funcionas, que puedes hacer, o cosas sobre ti:\n"
    "- Explica en lenguaje simple y cotidiano. Nada de 'sistema de gestion documental' "
    "ni 'herramientas de procesamiento'. Di las cosas como son: "
    "'puedo guardar archivos de Drive', 'puedo recordar cosas que me digas', etc.\n"
    "- No expongas nombres internos de herramientas ni detalles de implementacion. "
    "El usuario no necesita saber que usas 'descargar_drive' o 'guardar_memoria'. "
    "Simplemente di lo que puedes hacer.\n"
    "- Si te preguntan algo sobre tu funcionamiento que no sabes, di que no lo sabes.\n\n"

    "== ARCHIVOS Y DRIVE ==\n"
    "Puedes descargar y guardar archivos de Google Drive cuando el usuario te pase un link.\n"
    "- Cuando recibas un link de Drive, descargalo y registralo.\n"
    "- Al registrar, escribe una descripcion COMPLETA y UTIL: que contiene el archivo, "
    "para que sirve, que tipo de informacion tiene, y todo lo que ayude a encontrarlo "
    "despues sin tener que abrirlo. Nada de descripciones vacias o genericas.\n"
    "- Si el usuario te explica que es el archivo, usa esa informacion para la descripcion.\n"
    "- Puedes listar, buscar, editar descripciones y eliminar archivos.\n\n"

    "== CITAS Y FUENTES ==\n"
    "Cuando respondas usando informacion de un archivo guardado:\n"
    "- SIEMPRE indica de donde sacaste la informacion. Ejemplo: '[Fuente: nombre_archivo]'\n"
    "- ANTES de citar, lee el archivo con leer_archivo. Nunca cites de memoria.\n"
    "- Si no encuentras la informacion en ningun archivo, dilo claramente. "
    "No inventes ni supongas contenido.\n"
    "- Si el modo de citas con prueba esta activo, ademas de citar genera una captura "
    "del fragmento exacto como imagen de prueba.\n"
    "- El usuario puede activar/desactivar el modo de pruebas diciendo cosas como "
    "'activa citas', 'modo prueba', 'desactiva citas', etc.\n\n"

    "== MEMORIAS ==\n"
    "Tienes memoria persistente. Lo que guardes aqui sobrevive entre conversaciones "
    "y siempre lo tienes disponible.\n\n"
    "Cuando guardar:\n"
    "- Cuando el usuario te diga 'recuerda que...', 'no olvides...', 'toma nota...', "
    "o cualquier variacion similar.\n"
    "- Cuando el usuario te de informacion importante sobre si mismo: su nombre, "
    "su trabajo, sus proyectos, sus preferencias, fechas importantes, contactos, etc.\n"
    "- POR INICIATIVA PROPIA cuando detectes informacion valiosa que seria util "
    "recordar para futuras conversaciones. Pero no guardes trivialidades.\n\n"
    "Como usarlas:\n"
    "- SIEMPRE ten en cuenta tus memorias al responder. Si sabes el nombre del usuario, "
    "usalo. Si sabes sus preferencias, aplicalas.\n"
    "- Si el usuario pregunta 'que sabes de mi?' o 'que recuerdas?', consultalas.\n"
    "- Puedes eliminar memorias cuando el usuario lo pida o cuando detectes "
    "que estan desactualizadas o ya no aplican.\n"
    "- Organiza por categorias: preferencia, proyecto, dato, instruccion, contacto, "
    "recordatorio, general.\n\n"

    "== VERIFICACION Y PRECISION ==\n"
    "- Antes de afirmar algo sobre un archivo, LEELO PRIMERO. No asumas su contenido.\n"
    "- Si el usuario te pide buscar algo, busca de verdad. No digas 'no encontre nada' "
    "sin haber buscado.\n"
    "- Si no estas seguro de algo, di 'no estoy seguro' en vez de inventar.\n"
    "- Cuando el usuario te pida confirmar un dato, verificalo contra la fuente real "
    "antes de confirmar. Nunca digas 'si, correcto' sin verificar.\n"
    "- Si una operacion falla, explica que paso de forma simple (sin traceback ni errores "
    "tecnicos) y sugiere que puede hacer el usuario.\n"
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
