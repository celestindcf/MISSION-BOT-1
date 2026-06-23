import discord
from discord.ext import commands
import config
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    try:
        await bot.load_extension("cogs.dispatch")
        await bot.load_extension("cogs.missions")
        await bot.load_extension("cogs.agents")
        await bot.load_extension("cogs.config_cog")
        print("✅ Modules chargés")
    except Exception as e:
        print(f"❌ Erreur : {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Permission refusée.")
    else:
        await ctx.send(f"❌ Erreur: {error}")

if __name__ == "__main__":
    if not config.TOKEN:
        print("❌ Token manquant")
    else:
        bot.run(config.TOKEN)
