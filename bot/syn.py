from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config.settings import settings
from services.openrouter_service import openrouter_service


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola, soy *Syn*, el asistente de Cortex.\n\n"
        "Escribe cualquier mensaje y te respondo.\n"
        "Puedes pasarme links de Google Drive y los guardo con su descripcion.\n\n"
        "Comandos:\n"
        "/estado - Estado del sistema\n"
        "/archivos - Ver archivos guardados\n"
        "/memorias - Ver memorias guardadas\n"
        "/citas - Activar/desactivar modo citas con prueba\n"
        "/limpiar - Limpiar historial\n"
        "/ayuda - Ver comandos",
        parse_mode="Markdown",
    )


async def _enviar_respuesta(update: Update, resultado: dict):
    """Envia texto y opcionalmente imagenes de captura."""
    texto = resultado["texto"]
    imagenes = resultado.get("imagenes", [])

    # Enviar texto
    if len(texto) > 4096:
        for i in range(0, len(texto), 4096):
            await update.message.reply_text(texto[i : i + 4096])
    else:
        await update.message.reply_text(texto)

    # Enviar imagenes de captura como prueba
    for ruta_img in imagenes:
        try:
            with open(ruta_img, "rb") as foto:
                await update.message.reply_photo(
                    photo=foto,
                    caption="Captura de la fuente citada",
                )
        except Exception as e:
            await update.message.reply_text(f"No pude enviar la captura: {e}")


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texto = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        resultado = await openrouter_service.ask(texto, user_id)
    except Exception as e:
        resultado = {"texto": f"Error al contactar la IA: {e}", "imagenes": []}

    await _enviar_respuesta(update, resultado)


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.tools import get_modo_citas

    user_id = str(update.effective_user.id)
    modo = "Activo" if get_modo_citas(user_id) else "Inactivo"
    texto = (
        "*Estado de Cortex*\n\n"
        "Bot: Activo\n"
        "IA: Conectada\n"
        f"Modelo: `{settings.OPENROUTER_MODEL}`\n"
        f"Modo citas con prueba: {modo}\n\n"
        "_Cortex - Asistencia operativa con IA_"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    openrouter_service.histories.pop(user_id, None)
    await update.message.reply_text("Historial limpiado.")


async def archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.drive_service import listar_registro

    registro = listar_registro()
    if len(registro) > 4096:
        for i in range(0, len(registro), 4096):
            await update.message.reply_text(registro[i : i + 4096])
    else:
        await update.message.reply_text(registro)


async def citas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.tools import get_modo_citas, set_modo_citas

    user_id = str(update.effective_user.id)
    actual = get_modo_citas(user_id)
    nuevo = not actual
    set_modo_citas(user_id, nuevo)

    if nuevo:
        await update.message.reply_text(
            "*Modo citas con prueba: ACTIVADO*\n\n"
            "Ahora cuando cite informacion de un archivo, "
            "generare una captura del texto original como prueba.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "*Modo citas con prueba: DESACTIVADO*\n\n"
            "Seguire citando las fuentes pero sin generar capturas.",
            parse_mode="Markdown",
        )


async def memorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.memory_service import listar_memorias

    resultado = listar_memorias()
    if len(resultado) > 4096:
        for i in range(0, len(resultado), 4096):
            await update.message.reply_text(resultado[i : i + 4096])
    else:
        await update.message.reply_text(resultado)


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.tools import get_modo_citas

    user_id = str(update.effective_user.id)
    modo = "Activo" if get_modo_citas(user_id) else "Inactivo"
    await update.message.reply_text(
        "*Comandos de Syn*\n\n"
        "/inicio - Mensaje de bienvenida\n"
        "/estado - Estado del sistema\n"
        "/archivos - Ver archivos guardados\n"
        "/memorias - Ver memorias guardadas\n"
        f"/citas - Toggle modo citas con prueba (actual: {modo})\n"
        "/limpiar - Limpiar historial\n"
        "/ayuda - Ver este mensaje\n\n"
        "Tambien puedes:\n"
        "- Enviarme un link de Drive y lo guardo\n"
        "- Decirme 'recuerda que...' y lo memorizo\n"
        "- Pedirme que busque o edite descripciones\n"
        "- Decirme 'activa citas' o 'desactiva citas'\n"
        "- Escribir cualquier pregunta",
        parse_mode="Markdown",
    )


def run_bot():
    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("archivos", archivos))
    app.add_handler(CommandHandler("citas", citas))
    app.add_handler(CommandHandler("memorias", memorias))
    app.add_handler(CommandHandler("limpiar", limpiar))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))

    print("[Syn] Bot de Telegram iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
