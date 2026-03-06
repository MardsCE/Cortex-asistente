import discord
from discord.ext import commands
from config.settings import settings
from services.openrouter_service import openrouter_service

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=settings.DISCORD_PREFIX, intents=intents)


@bot.event
async def on_ready():
    print(f"[Syn] Conectado como {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"Cortex | {settings.DISCORD_PREFIX}help",
        )
    )


@bot.command(name="syn", help="Habla con Syn, el asistente de Cortex.")
async def syn_command(ctx: commands.Context, *, mensaje: str):
    async with ctx.typing():
        try:
            response = await openrouter_service.ask(mensaje, str(ctx.author.id))
        except Exception as e:
            response = f"Error al contactar la IA: {e}"

    # Discord tiene límite de 2000 caracteres
    if len(response) > 2000:
        for i in range(0, len(response), 2000):
            await ctx.send(response[i : i + 2000])
    else:
        await ctx.send(response)


@bot.command(name="status", help="Muestra el estado del sistema.")
async def status_command(ctx: commands.Context):
    latency_ms = round(bot.latency * 1000, 2)
    embed = discord.Embed(
        title="Estado de Cortex",
        color=discord.Color.green(),
    )
    embed.add_field(name="Bot", value="Online", inline=True)
    embed.add_field(name="IA", value="Activa", inline=True)
    embed.add_field(name="Latencia", value=f"{latency_ms} ms", inline=True)
    embed.set_footer(text="Cortex - Plataforma de asistencia operativa")
    await ctx.send(embed=embed)


@bot.command(name="ping", help="Verifica la latencia del bot.")
async def ping_command(ctx: commands.Context):
    latency_ms = round(bot.latency * 1000, 2)
    await ctx.send(f"Pong! Latencia: {latency_ms} ms")


def run_bot():
    bot.run(settings.DISCORD_TOKEN)
