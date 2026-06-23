import discord
from discord.ext import commands
import config
import os
from threading import Thread

# ========== SERVEUR HTTP FACTICE POUR RENDER ==========
def keep_alive():
    try:
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "🖤 Mission Dispatch Bot is running!"
        
        @app.route('/health')
        def health():
            return "OK", 200
        
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except ImportError:
        print("⚠️ Flask non installé, serveur HTTP factice désactivé.")
    except Exception as e:
        print(f"⚠️ Erreur serveur HTTP: {e}")

# Démarrer le serveur HTTP dans un thread séparé
Thread(target=keep_alive, daemon=True).start()
print("✅ Serveur HTTP factice démarré")

# ========== BOT DISCORD ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    print(f"📡 Connecté sur {len(bot.guilds)} serveurs")
    
    try:
        await bot.load_extension("cogs.dispatch")
        await bot.load_extension("cogs.missions")
        await bot.load_extension("cogs.agents")
        await bot.load_extension("cogs.config_cog")
        print("✅ Tous les modules chargés")
    except Exception as e:
        print(f"❌ Erreur chargement des modules: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Permission refusée.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argument manquant. Vérifie la commande.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Commande inconnue. Utilise `!help` pour voir les commandes.")
    else:
        await ctx.send(f"❌ Erreur: {error}")

@bot.command(name="ping")
async def ping(ctx):
    """Vérifie la latence du bot"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong ! Latence : {latency}ms")

@bot.command(name="servers")
async def list_servers(ctx):
    """Liste les serveurs où le bot est présent"""
    if not await is_owner(ctx.author):
        await ctx.send("❌ Commande réservée au propriétaire.")
        return
    
    servers = "\n".join([f"• {g.name} ({g.id})" for g in bot.guilds])
    await ctx.send(f"📡 Serveurs :\n{servers}")

async def is_owner(user):
    return user.id == config.OWNER_ID if hasattr(config, 'OWNER_ID') else False

if __name__ == "__main__":
    if not config.TOKEN:
        print("❌ Token Discord manquant. Définis la variable d'environnement DISCORD_TOKEN")
    else:
        print("🚀 Démarrage du bot...")
        bot.run(config.TOKEN)
