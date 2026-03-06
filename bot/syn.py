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


def _autorizado(user_id: str) -> bool:
    """Verifica si el usuario esta en la whitelist. Si no hay whitelist, permite todos."""
    if not settings.ALLOWED_USERS:
        return True
    return user_id in settings.ALLOWED_USERS


async def _check_auth(update: Update) -> bool:
    """Verifica autorizacion y envia mensaje de rechazo si no esta autorizado."""
    user_id = str(update.effective_user.id)
    if not _autorizado(user_id):
        await update.message.reply_text("No tienes acceso a este bot.")
        return False
    return True


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    await update.message.reply_text(
        "Hola, soy *Syn*, el asistente de Cortex.\n\n"
        "Escribe cualquier mensaje y te respondo.\n"
        "Puedes pasarme links de Google Drive y los guardo con su descripcion.\n\n"
        "Comandos:\n"
        "/estado - Estado del sistema\n"
        "/archivos - Ver archivos guardados\n"
        "/memorias - Ver memorias guardadas\n"
        "/recordatorios - Ver recordatorios activos\n"
        "/metas - Ver metas activas\n"
        "/logs - Ver actividad del dia\n"
        "/citas - Activar/desactivar modo citas con prueba\n"
        "/limpiar - Limpiar historial\n"
        "/ayuda - Ver comandos",
        parse_mode="Markdown",
    )


async def _enviar_respuesta(update: Update, resultado: dict):
    """Envia texto y opcionalmente imagenes de captura."""
    texto = resultado["texto"]
    imagenes = resultado.get("imagenes", [])

    if len(texto) > 4096:
        for i in range(0, len(texto), 4096):
            await update.message.reply_text(texto[i : i + 4096])
    else:
        await update.message.reply_text(texto)

    for ruta_img in imagenes:
        try:
            with open(ruta_img, "rb") as foto:
                await update.message.reply_photo(
                    photo=foto,
                    caption="Captura de la fuente citada",
                )
        except Exception:
            await update.message.reply_text("No pude enviar la captura.")


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    user_id = str(update.effective_user.id)
    texto = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        resultado = await openrouter_service.ask(texto, user_id, chat_id=str(update.effective_chat.id))
    except Exception:
        resultado = {"texto": "Hubo un error al procesar tu mensaje. Intenta de nuevo.", "imagenes": []}

    await _enviar_respuesta(update, resultado)


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    from services.tools import get_modo_citas

    user_id = str(update.effective_user.id)
    modo = "Activo" if get_modo_citas(user_id) else "Inactivo"
    texto = (
        "*Estado de Cortex*\n\n"
        "Bot: Activo\n"
        "IA: Conectada\n"
        f"Modelo: `{settings.OPENROUTER_MODEL}`\n"
        f"Zona horaria: {settings.TIMEZONE}\n"
        f"Modo citas con prueba: {modo}\n\n"
        "_Cortex - Asistencia operativa con IA_"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    user_id = str(update.effective_user.id)
    openrouter_service.histories.pop(user_id, None)
    await update.message.reply_text("Historial limpiado.")


async def archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    from services.drive_service import listar_registro

    user_id = str(update.effective_user.id)
    registro = listar_registro(user_id)
    if len(registro) > 4096:
        for i in range(0, len(registro), 4096):
            await update.message.reply_text(registro[i : i + 4096])
    else:
        await update.message.reply_text(registro)


async def citas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
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
    if not await _check_auth(update):
        return
    from services.memory_service import listar_memorias

    user_id = str(update.effective_user.id)
    resultado = listar_memorias(user_id)
    if len(resultado) > 4096:
        for i in range(0, len(resultado), 4096):
            await update.message.reply_text(resultado[i : i + 4096])
    else:
        await update.message.reply_text(resultado)


async def recordatorios_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    from services.reminder_service import listar_recordatorios

    user_id = str(update.effective_user.id)
    resultado = listar_recordatorios(user_id)
    if len(resultado) > 4096:
        for i in range(0, len(resultado), 4096):
            await update.message.reply_text(resultado[i : i + 4096])
    else:
        await update.message.reply_text(resultado)


async def metas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    from services.goals_service import listar_metas

    user_id = str(update.effective_user.id)
    resultado = listar_metas(user_id, solo_activas=True)
    if len(resultado) > 4096:
        for i in range(0, len(resultado), 4096):
            await update.message.reply_text(resultado[i : i + 4096])
    else:
        await update.message.reply_text(resultado)


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    from services.log_service import obtener_log

    user_id = str(update.effective_user.id)
    fecha = context.args[0] if context.args else None
    resultado = obtener_log(fecha, user_id=user_id)
    if len(resultado) > 4096:
        for i in range(0, len(resultado), 4096):
            await update.message.reply_text(resultado[i : i + 4096])
    else:
        await update.message.reply_text(resultado)


async def _verificar_recordatorios(context: ContextTypes.DEFAULT_TYPE):
    """Job que se ejecuta cada minuto para enviar recordatorios pendientes."""
    from services.reminder_service import obtener_recordatorios_pendientes
    from services import log_service

    pendientes = obtener_recordatorios_pendientes()
    for r in pendientes:
        try:
            await context.bot.send_message(
                chat_id=r["chat_id"],
                text=f"Recordatorio\n\n{r['contenido']}",
            )
            log_service.log_recordatorio(r["user_id"], r["id"], r["contenido"])
        except Exception as e:
            log_service.log_error(r.get("user_id", "?"), "recordatorio", str(e))
            print(f"[Syn] Error enviando recordatorio #{r['id']}: {e}")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    from services.tools import get_modo_citas

    user_id = str(update.effective_user.id)
    modo = "Activo" if get_modo_citas(user_id) else "Inactivo"
    await update.message.reply_text(
        "Comandos de Syn\n\n"
        "/inicio - Mensaje de bienvenida\n"
        "/estado - Estado del sistema\n"
        "/archivos - Ver archivos guardados\n"
        "/memorias - Ver memorias guardadas\n"
        "/recordatorios - Ver recordatorios programados\n"
        "/metas - Ver metas activas\n"
        "/logs - Ver actividad del dia\n"
        f"/citas - Toggle modo citas con prueba (actual: {modo})\n"
        "/limpiar - Limpiar historial\n"
        "/ayuda - Ver este mensaje\n\n"
        "Tambien puedes:\n"
        "- Enviarme un link de Drive y lo guardo\n"
        "- Decirme 'recuerda que...' y lo memorizo\n"
        "- Pedirme que busque o edite descripciones\n"
        "- Decirme 'avisame a las 9am...' y te programo un recordatorio\n"
        "- Decirme 'quiero lograr...' y te creo una meta con pasos\n"
        "- Pedirme buscar algo en internet\n"
        "- Decirme 'activa citas' o 'desactiva citas'\n"
        "- Escribir cualquier pregunta",
    )


def run_bot():
    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("archivos", archivos))
    app.add_handler(CommandHandler("citas", citas))
    app.add_handler(CommandHandler("memorias", memorias))
    app.add_handler(CommandHandler("recordatorios", recordatorios_cmd))
    app.add_handler(CommandHandler("metas", metas_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))
    app.add_handler(CommandHandler("limpiar", limpiar))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))

    # Scheduler: verificar recordatorios cada 60 segundos
    app.job_queue.run_repeating(_verificar_recordatorios, interval=60, first=10)

    from services import log_service
    log_service.log_sistema("Bot de Telegram iniciado")
    log_service.log_sistema("Scheduler de recordatorios activo (cada 60s)")

    print("[Syn] Bot de Telegram iniciado.")
    print("[Syn] Scheduler de recordatorios activo (cada 60s).")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
