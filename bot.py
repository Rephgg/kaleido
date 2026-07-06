import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "puntos.json"

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_datos(datos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

GUILD_ID = 1120824499198234807
GUILD = discord.Object(id=GUILD_ID)

@bot.event
async def on_ready():
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync(guild=None)
    await bot.tree.sync(guild=GUILD)
    print(f"Bot conectado como {bot.user}")

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="addpoints", description="Agrega puntos a un miembro", guild=GUILD)
@app_commands.describe(miembro="Miembro a añadir puntos", puntos="Cantidad de puntos")
async def addpoints(interaction: discord.Interaction, miembro: discord.Member, puntos: int):
    datos = cargar_datos()
    uid = str(miembro.id)
    if uid in datos:
        datos[uid]["puntos"] += puntos
    else:
        datos[uid] = {"nombre": miembro.display_name, "puntos": puntos}
    guardar_datos(datos)
    await interaction.response.send_message(
        f"{puntos} puntos agregados a {miembro.mention}. Total: {datos[uid]['puntos']}"
    )

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="setpoints", description="Establece los puntos exactos de un miembro", guild=GUILD)
@app_commands.describe(miembro="Miembro a modificar", puntos="Nuevos puntos")
async def setpoints(interaction: discord.Interaction, miembro: discord.Member, puntos: int):
    datos = cargar_datos()
    uid = str(miembro.id)
    datos[uid] = {"nombre": miembro.display_name, "puntos": puntos}
    guardar_datos(datos)
    await interaction.response.send_message(f"Puntos de {miembro.mention} actualizados a {puntos}")

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="delpoints", description="Elimina un miembro de la lista de puntos", guild=GUILD)
@app_commands.describe(miembro="Miembro a eliminar")
async def delpoints(interaction: discord.Interaction, miembro: discord.Member):
    datos = cargar_datos()
    uid = str(miembro.id)
    if uid not in datos:
        return await interaction.response.send_message("Ese usuario no tiene puntos registrados.")
    del datos[uid]
    guardar_datos(datos)
    await interaction.response.send_message(f"{miembro.mention} eliminado de la lista de puntos.")

@bot.tree.command(name="setcanal", description="Configura el canal para respuestas de ranking y puntos", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal donde se enviarán las respuestas")
async def setcanal(interaction: discord.Interaction, canal: discord.TextChannel):
    config = cargar_config()
    config["canal_puntos"] = canal.id
    guardar_config(config)
    await interaction.response.send_message(f"Canal de respuestas configurado a {canal.mention}", ephemeral=True)

@bot.tree.command(name="delcanal", description="Elimina la configuración del canal de respuestas", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def delcanal(interaction: discord.Interaction):
    config = cargar_config()
    if "canal_puntos" not in config:
        return await interaction.response.send_message("No hay un canal configurado.", ephemeral=True)
    del config["canal_puntos"]
    guardar_config(config)
    await interaction.response.send_message("Canal de respuestas eliminado. Ahora las respuestas vuelven al canal actual.", ephemeral=True)

def construir_ranking(datos):
    if not datos:
        return None
    ordenados = sorted(datos.items(), key=lambda x: x[1]["puntos"], reverse=True)
    mensaje = "# Ranking general del servidor\n\n"
    mensaje += f"\n _Este ranking es un conteo de puntos del servidor, estos se adquieren por participación constante en torneos y quedar en el top 3 del mismo._ \n\n"
    for i, (uid, u) in enumerate(ordenados, 1):
        mensaje += f"**{i}.** <@{uid}> - {u['puntos']} pts\n"
    from datetime import datetime
    mensaje += f"\n|| Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')} ||"
    return mensaje

@bot.tree.command(name="ranking", description="Muestra la lista de todos los usuarios con puntos", guild=GUILD)
async def ranking(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    config = cargar_config()
    datos = cargar_datos()
    mensaje = construir_ranking(datos)
    if not mensaje:
        return await interaction.followup.send("No hay usuarios registrados.", ephemeral=True)
    canal_id = config.get("canal_puntos")
    if canal_id:
        canal = bot.get_channel(int(canal_id))
        if canal:
            msg = await canal.send(mensaje)
            config["ranking_msg_id"] = msg.id
            config["ranking_channel_id"] = canal.id
            guardar_config(config)
            await interaction.followup.send(f"Ranking enviado a {canal.mention}", ephemeral=True)
            return
    msg = await interaction.followup.send(mensaje, ephemeral=True)
    config["ranking_msg_id"] = msg.id
    config["ranking_channel_id"] = interaction.channel_id
    guardar_config(config)

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="updateranking", description="Actualiza el mensaje del ranking con los datos más recientes", guild=GUILD)
async def updateranking(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    config = cargar_config()
    msg_id = config.get("ranking_msg_id")
    channel_id = config.get("ranking_channel_id")
    if not msg_id or not channel_id:
        return await interaction.followup.send("Primero ejecutá /ranking para crear el mensaje.", ephemeral=True)
    canal = bot.get_channel(int(channel_id))
    if not canal:
        return await interaction.followup.send("No se encontró el canal del mensaje.", ephemeral=True)
    try:
        msg = await canal.fetch_message(int(msg_id))
    except discord.NotFound:
        return await interaction.followup.send("El mensaje original fue eliminado. Ejecutá /ranking de nuevo.", ephemeral=True)
    datos = cargar_datos()
    mensaje = construir_ranking(datos)
    if not mensaje:
        return await interaction.followup.send("No hay usuarios registrados.", ephemeral=True)
    await msg.edit(content=mensaje)
    await interaction.followup.send("Ranking actualizado.", ephemeral=True)

@bot.tree.command(name="puntos", description="Muestra los puntos de un miembro o los tuyos", guild=GUILD)
@app_commands.describe(miembro="Miembro a consultar (opcional)")
async def puntos(interaction: discord.Interaction, miembro: discord.Member = None):
    await interaction.response.defer(ephemeral=True)
    config = cargar_config()
    miembro = miembro or interaction.user
    datos = cargar_datos()
    uid = str(miembro.id)
    if uid not in datos:
        return await interaction.followup.send(f"{miembro.mention} no tiene puntos registrados.", ephemeral=True)
    canal_id = config.get("canal_puntos")
    if canal_id:
        canal = bot.get_channel(int(canal_id))
        if canal:
            await canal.send(f"{miembro.mention} tiene **{datos[uid]['puntos']}** puntos.")
            await interaction.followup.send(f"Respuesta enviada a {canal.mention}", ephemeral=True)
            return
    await interaction.followup.send(f"{miembro.mention} tiene **{datos[uid]['puntos']}** puntos.", ephemeral=True)

@bot.tree.command(name="help", description="Muestra todos los comandos disponibles", guild=GUILD)
async def help(interaction: discord.Interaction):
    es_admin = interaction.user.guild_permissions.administrator
    txt = "**📋 Comandos del Bot**\n\n"
    txt += "**📊 Puntos**\n"
    txt += "`/ranking` - Muestra el ranking de todos los usuarios\n"
    txt += "`/puntos [@user]` - Consulta tus puntos o los de otro\n"
    txt += "`/updateranking` - Actualiza el mensaje del ranking\n"
    if es_admin:
        txt += "\n**🔧 Admin**\n"
        txt += "`/addpoints @user <pts>` - Agrega puntos a un usuario\n"
        txt += "`/setpoints @user <pts>` - Asigna puntos exactos\n"
        txt += "`/delpoints @user` - Elimina usuario de la lista\n"
        txt += "`/setcanal #canal` - Configura canal de respuestas\n"
        txt += "`/delcanal` - Elimina canal configurado\n"
    await interaction.response.send_message(txt, ephemeral=True)

@addpoints.error
@setpoints.error
@delpoints.error
async def perm_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("No tenés permiso para usar este comando.", ephemeral=True)

bot.run(TOKEN)
