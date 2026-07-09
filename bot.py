import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = mongo_client["kaleido"]
coleccion_puntos = db["puntos"]

def _cargar_datos():
    docs = list(coleccion_puntos.find())
    return {d["_id"]: {"nombre": d["nombre"], "puntos": d["puntos"]} for d in docs}

def _agregar_puntos(user_id, nombre, cantidad):
    coleccion_puntos.update_one(
        {"_id": user_id},
        {"$inc": {"puntos": cantidad}, "$set": {"nombre": nombre}},
        upsert=True
    )
    doc = coleccion_puntos.find_one({"_id": user_id})
    return doc["puntos"]

def _setear_puntos(user_id, nombre, puntos):
    coleccion_puntos.update_one(
        {"_id": user_id},
        {"$set": {"nombre": nombre, "puntos": puntos}},
        upsert=True
    )

def _eliminar_usuario(user_id):
    coleccion_puntos.delete_one({"_id": user_id})

def _obtener_puntos(user_id):
    doc = coleccion_puntos.find_one({"_id": user_id})
    return doc["puntos"] if doc else None

async def cargar_datos():
    return await asyncio.to_thread(_cargar_datos)

async def agregar_puntos(user_id, nombre, cantidad):
    return await asyncio.to_thread(_agregar_puntos, user_id, nombre, cantidad)

async def setear_puntos(user_id, nombre, puntos):
    await asyncio.to_thread(_setear_puntos, user_id, nombre, puntos)

async def eliminar_usuario(user_id):
    await asyncio.to_thread(_eliminar_usuario, user_id)

async def obtener_puntos(user_id):
    return await asyncio.to_thread(_obtener_puntos, user_id)

def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="addpoints", description="Agrega puntos a un miembro")
@app_commands.describe(miembro="Miembro a añadir puntos", puntos="Cantidad de puntos")
async def addpoints(interaction: discord.Interaction, miembro: discord.Member, puntos: int):
    uid = str(miembro.id)
    total = await agregar_puntos(uid, miembro.display_name, puntos)
    await interaction.response.send_message(
        f"{puntos} puntos agregados a {miembro.mention}. Total: {total}"
    )

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="setpoints", description="Establece los puntos exactos de un miembro")
@app_commands.describe(miembro="Miembro a modificar", puntos="Nuevos puntos")
async def setpoints(interaction: discord.Interaction, miembro: discord.Member, puntos: int):
    await setear_puntos(str(miembro.id), miembro.display_name, puntos)
    await interaction.response.send_message(f"Puntos de {miembro.mention} actualizados a {puntos}")

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="delpoints", description="Elimina un miembro de la lista de puntos")
@app_commands.describe(miembro="Miembro a eliminar")
async def delpoints(interaction: discord.Interaction, miembro: discord.Member):
    uid = str(miembro.id)
    if not await obtener_puntos(uid):
        return await interaction.response.send_message("Ese usuario no tiene puntos registrados.")
    await eliminar_usuario(uid)
    await interaction.response.send_message(f"{miembro.mention} eliminado de la lista de puntos.")

@bot.tree.command(name="setcanal", description="Configura el canal para respuestas de ranking y puntos")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal donde se enviarán las respuestas")
async def setcanal(interaction: discord.Interaction, canal: discord.TextChannel):
    config = cargar_config()
    config["canal_puntos"] = canal.id
    guardar_config(config)
    await interaction.response.send_message(f"Canal de respuestas configurado a {canal.mention}", ephemeral=True)

@bot.tree.command(name="delcanal", description="Elimina la configuración del canal de respuestas")
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
    from datetime import datetime
    ordenados = sorted(datos.items(), key=lambda x: x[1]["puntos"], reverse=True)
    desc = "_Este ranking es un conteo de puntos del servidor, estos se adquieren por participación constante en torneos y quedar en el top 3 del mismo._\n"
    embed = discord.Embed(title="# Ranking general del servidor", description=desc, color=0xF1C40F)
    top3 = ""
    resto = ""
    for i, (uid, u) in enumerate(ordenados, 1):
        linea = f"**{i}.** <@{uid}> — {u['puntos']} pts\n"
        if i <= 3:
            top3 += linea
        else:
            resto += linea
    if top3:
        embed.add_field(name="Top 3", value=top3, inline=False)
    if resto:
        embed.add_field(name="Resto del ranking", value=resto, inline=False)
    embed.set_footer(text=f"Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    return embed

@bot.tree.command(name="ranking", description="Muestra la lista de todos los usuarios con puntos")
async def ranking(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    config = cargar_config()
    datos = await cargar_datos()
    embed = construir_ranking(datos)
    if not embed:
        return await interaction.followup.send("No hay usuarios registrados.", ephemeral=True)
    canal_id = config.get("canal_puntos")
    if canal_id:
        canal = bot.get_channel(int(canal_id))
        if canal:
            msg = await canal.send(embed=embed)
            config["ranking_msg_id"] = msg.id
            config["ranking_channel_id"] = canal.id
            guardar_config(config)
            await interaction.followup.send(f"Ranking enviado a {canal.mention}", ephemeral=True)
            return
    msg = await interaction.followup.send(embed=embed, ephemeral=True)
    config["ranking_msg_id"] = msg.id
    config["ranking_channel_id"] = interaction.channel_id
    guardar_config(config)

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="updateranking", description="Actualiza el mensaje del ranking con los datos más recientes")
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
    datos = await cargar_datos()
    embed = construir_ranking(datos)
    if not embed:
        return await interaction.followup.send("No hay usuarios registrados.", ephemeral=True)
    await msg.edit(embed=embed)
    await interaction.followup.send("Ranking actualizado.", ephemeral=True)

@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="say", description="El bot repite el texto que escribas")
@app_commands.describe(texto="Texto que quieres que diga el bot")
async def say(interaction: discord.Interaction, texto: str):
    await interaction.response.send_message(texto)

@bot.tree.command(name="puntos", description="Muestra los puntos de un miembro o los tuyos")
@app_commands.describe(miembro="Miembro a consultar (opcional)")
async def puntos(interaction: discord.Interaction, miembro: discord.Member = None):
    await interaction.response.defer(ephemeral=True)
    config = cargar_config()
    miembro = miembro or interaction.user
    uid = str(miembro.id)
    total = await obtener_puntos(uid)
    if total is None:
        return await interaction.followup.send(f"{miembro.mention} no tiene puntos registrados.", ephemeral=True)
    texto = f"{miembro.mention} tiene **{total}** puntos."
    canal_id = config.get("canal_puntos")
    if canal_id:
        canal = bot.get_channel(int(canal_id))
        if canal:
            await canal.send(texto)
            await interaction.followup.send(f"Respuesta enviada a {canal.mention}", ephemeral=True)
            return
    await interaction.followup.send(texto, ephemeral=True)

@bot.tree.command(name="help", description="Muestra todos los comandos disponibles")
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

from aiohttp import web

async def health(request):
    return web.Response(text="Bot online")

async def run_http():
    PORT = int(os.getenv("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await run_http()
    await bot.start(TOKEN)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
