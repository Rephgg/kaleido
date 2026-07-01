import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

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

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="addpoints", description="Agrega puntos a un miembro")
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
@bot.tree.command(name="setpoints", description="Establece los puntos exactos de un miembro")
@app_commands.describe(miembro="Miembro a modificar", puntos="Nuevos puntos")
async def setpoints(interaction: discord.Interaction, miembro: discord.Member, puntos: int):
    datos = cargar_datos()
    uid = str(miembro.id)
    datos[uid] = {"nombre": miembro.display_name, "puntos": puntos}
    guardar_datos(datos)
    await interaction.response.send_message(f"Puntos de {miembro.mention} actualizados a {puntos}")

@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="delpoints", description="Elimina un miembro de la lista de puntos")
@app_commands.describe(miembro="Miembro a eliminar")
async def delpoints(interaction: discord.Interaction, miembro: discord.Member):
    datos = cargar_datos()
    uid = str(miembro.id)
    if uid not in datos:
        return await interaction.response.send_message("Ese usuario no tiene puntos registrados.")
    del datos[uid]
    guardar_datos(datos)
    await interaction.response.send_message(f"{miembro.mention} eliminado de la lista de puntos.")

@bot.tree.command(name="ranking", description="Muestra la lista de todos los usuarios con puntos")
async def ranking(interaction: discord.Interaction):
    datos = cargar_datos()
    if not datos:
        return await interaction.response.send_message("No hay usuarios registrados.")
    ordenados = sorted(datos.values(), key=lambda x: x["puntos"], reverse=True)
    mensaje = "**🏆 Ranking de Puntos 🏆**\n\n"
    for i, u in enumerate(ordenados, 1):
        mensaje += f"{i}. **{u['nombre']}** - {u['puntos']} pts\n"
    await interaction.response.send_message(mensaje)

@bot.tree.command(name="puntos", description="Muestra los puntos de un miembro o los tuyos")
@app_commands.describe(miembro="Miembro a consultar (opcional)")
async def puntos(interaction: discord.Interaction, miembro: discord.Member = None):
    miembro = miembro or interaction.user
    datos = cargar_datos()
    uid = str(miembro.id)
    if uid not in datos:
        return await interaction.response.send_message(f"{miembro.mention} no tiene puntos registrados.")
    await interaction.response.send_message(f"{miembro.mention} tiene **{datos[uid]['puntos']}** puntos.")

@addpoints.error
@setpoints.error
@delpoints.error
async def perm_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("No tenés permiso para usar este comando.", ephemeral=True)

bot.run(TOKEN)
