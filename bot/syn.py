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
        "Escribe cualquier mensaje y te respondo.\n\n"
        "Comandos:\n"
        "/estado - Estado del sistema\n"
        "/limpiar - Limpiar historial\n"
        "/ayuda - Ver comandos",
        parse_mode="Markdown",
    )


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texto = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        respuesta = await openrouter_service.ask(texto, user_id)
    except Exception as e:
        respuesta = f"Error al contactar la IA: {e}"

    if len(respuesta) > 4096:
        for i in range(0, len(respuesta), 4096):
            await update.message.reply_text(respuesta[i : i + 4096])
    else:
        await update.message.reply_text(respuesta)


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "*Estado de Cortex*\n\n"
        "Bot: Activo\n"
        "IA: Conectada\n"
        f"Modelo: `{settings.OPENROUTER_MODEL}`\n\n"
        "_Cortex - Asistencia operativa con IA_"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    openrouter_service.histories.pop(user_id, None)
    await update.message.reply_text("Historial limpiado.")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Comandos de Syn*\n\n"
        "/inicio - Mensaje de bienvenida\n"
        "/estado - Estado del sistema\n"
        "/limpiar - Limpiar historial\n"
        "/ayuda - Ver este mensaje\n\n"
        "O simplemente escribe lo que necesites.",
        parse_mode="Markdown",
    )


def run_bot():
    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("limpiar", limpiar))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))

    print("[Syn] Bot de Telegram iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
