import os
from datetime import date, timedelta

import discord
import pandas as pd
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
RUTA_CSV = os.getenv("CSV_PATH")
GUILD_ID = os.getenv("GUILD_ID")  # opcional: los comandos aparecen al instante

COLOR = 0x6EA8FF  # color de la barrita del mensaje, cambialo si querés


def formatear(minutos):
    """90 -> '1h 30m', 120 -> '2h', 25 -> '25m'."""
    h, m = divmod(int(minutos), 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def leer_sesiones():
    """Lee el CSV del tracker. Devuelve un DataFrame (puede estar vacío)."""
    df = pd.read_csv(RUTA_CSV, dtype=str).fillna("")
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    df["minutos"] = pd.to_numeric(df["minutos"], errors="coerce").fillna(0)
    return df


def calcular_resumen(df):
    hoy = date.today()
    por_dia = df.groupby("fecha")["minutos"].sum()
    dias_activos = set(por_dia.index)

    desde = hoy - timedelta(days=6)
    ultimos_7 = sum(m for d, m in por_dia.items() if desde <= d <= hoy)

    # Racha: días seguidos hasta hoy (o hasta ayer si hoy todavía no estudiaste)
    dia = hoy if hoy in dias_activos else hoy - timedelta(days=1)
    racha = 0
    while dia in dias_activos:
        racha += 1
        dia -= timedelta(days=1)

    return {
        "hoy": float(por_dia.get(hoy, 0)),
        "ultimos_7": float(ultimos_7),
        "total": float(df["minutos"].sum()),
        "dias": len(dias_activos),
        "racha": racha,
    }


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            servidor = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=servidor)
            await self.tree.sync(guild=servidor)
        else:
            await self.tree.sync()


bot = Bot()


@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")


@bot.tree.command(name="resumen", description="Tu resumen de estudio")
async def resumen(interaction: discord.Interaction):
    try:
        df = leer_sesiones()
    except Exception as e:
        print(f"Error leyendo el CSV: {e}")
        await interaction.response.send_message(
            "No pude leer tu archivo de sesiones. Revisá CSV_PATH en el .env.",
            ephemeral=True,
        )
        return

    if df.empty:
        await interaction.response.send_message(
            "Todavía no hay sesiones cargadas.", ephemeral=True
        )
        return

    r = calcular_resumen(df)
    embed = discord.Embed(title="📚 Resumen de estudio", color=COLOR)
    embed.add_field(name="Hoy", value=formatear(r["hoy"]))
    embed.add_field(name="Últimos 7 días", value=formatear(r["ultimos_7"]))
    embed.add_field(name="Racha", value=f"{r['racha']} d")
    embed.add_field(name="Total", value=formatear(r["total"]))
    embed.add_field(name="Días activos", value=str(r["dias"]))
    await interaction.response.send_message(embed=embed, ephemeral=True)


if not TOKEN or not RUTA_CSV:
    raise SystemExit("Falta DISCORD_TOKEN o CSV_PATH en el archivo .env")

bot.run(TOKEN)