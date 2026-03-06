import asyncio
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola, soy *Syn*, el asistente de Cortex.\n\n"
        "Escribe cualquier mensaje y te respondere.\n\n"
        "Comandos:\n"
        "/status - Estado del sistema\n"
        "/ping - Verificar latencia\n"
        "/clear - Limpiar historial de conversacion",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        response = await openrouter_service.ask(message, user_id)
    except Exception as e:
        response = f"Error al contactar la IA: {e}"

    # Telegram tiene limite de 4096 caracteres por mensaje
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await update.message.reply_text(response[i : i + 4096])
    else:
        await update.message.reply_text(response)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Estado de Cortex*\n\n"
        "Bot: Online\n"
        "IA: Activa\n"
        f"Modelo: `{settings.OPENROUTER_MODEL}`\n\n"
        "_Cortex - Plataforma de asistencia operativa_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong!")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    openrouter_service.histories.pop(user_id, None)
    await update.message.reply_text("Historial de conversacion limpiado.")


def run_bot():
    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[Syn] Bot de Telegram iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
