import discord
from discord.ext import commands
import config
import os
from threading import Thread
import json
from datetime import datetime

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

Thread(target=keep_alive, daemon=True).start()
print("✅ Serveur HTTP factice démarré")

# ========== BOT DISCORD ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

# ========== FONCTIONS BASE DE DONNÉES ==========
DATA_FILE = "data/missions.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"missions": [], "agents": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, default=str)

def create_mission(title, description, assigned_to=None):
    data = load_data()
    mission = {
        "id": len(data["missions"]) + 1,
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "status": "en attente",
        "created_at": datetime.now().isoformat()
    }
    data["missions"].append(mission)
    save_data(data)
    return mission

def assign_mission(mission_id, agent_id):
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            m["assigned_to"] = agent_id
            m["status"] = "en cours"
            save_data(data)
            return True
    return False

def get_missions_by_agent(agent_id):
    data = load_data()
    return [m for m in data["missions"] if m["assigned_to"] == agent_id]

def get_all_missions():
    data = load_data()
    return data["missions"]

def update_mission_status(mission_id, status):
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            m["status"] = status
            save_data(data)
            return True
    return False

def delete_mission(mission_id):
    data = load_data()
    data["missions"] = [m for m in data["missions"] if m["id"] != mission_id]
    save_data(data)
    return True

# ========== COMMANDES ==========

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    print(f"📡 Connecté sur {len(bot.guilds)} serveurs")
    print("✅ Toutes les commandes sont chargées")

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

@bot.command(name="assign")
async def assign_mission(ctx, membre: discord.Member, *, mission: str):
    """Assigne une mission à un agent"""
    result = create_mission(mission, f"Assignée par {ctx.author.display_name}", str(membre.id))
    assign_mission(result["id"], str(membre.id))
    
    embed = discord.Embed(
        title="📨 Nouvelle mission assignée",
        description=f"**{mission}**",
        color=discord.Color.green()
    )
    embed.add_field(name="Agent", value=membre.mention, inline=True)
    embed.add_field(name="ID", value=result["id"], inline=True)
    embed.set_footer(text=f"Par {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    
    try:
        await membre.send(f"📨 **Nouvelle mission**\n\n**{mission}**\n\nID: #{result['id']}")
    except:
        pass

@bot.command(name="missions")
async def list_missions(ctx):
    """Liste toutes les missions"""
    data = get_all_missions()
    if not data:
        await ctx.send("📭 Aucune mission.")
        return
    
    embed = discord.Embed(title="📋 Toutes les missions", color=discord.Color.blue())
    for m in data[-10:]:
        status_emoji = {
            "en attente": "⏳",
            "en cours": "🔄",
            "terminée": "✅",
            "annulée": "❌"
        }.get(m["status"], "❓")
        embed.add_field(
            name=f"{status_emoji} #{m['id']} - {m['title']}",
            value=f"Statut: {m['status']}\nAssignée à: <@{m['assigned_to']}>" if m["assigned_to"] else "Non assignée",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="my_missions")
async def my_missions(ctx):
    """Affiche les missions assignées à l'agent connecté"""
    missions = get_missions_by_agent(str(ctx.author.id))
    if not missions:
        await ctx.send("📭 Vous n'avez aucune mission assignée.")
        return
    
    embed = discord.Embed(
        title=f"📋 Missions de {ctx.author.display_name}",
        color=discord.Color.gold()
    )
    for m in missions:
        status_emoji = {
            "en attente": "⏳",
            "en cours": "🔄",
            "terminée": "✅",
            "annulée": "❌"
        }.get(m["status"], "❓")
        embed.add_field(
            name=f"{status_emoji} #{m['id']} - {m['title']}",
            value=f"Statut: {m['status']}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="complete")
async def complete_mission(ctx, mission_id: int):
    """Marque une mission comme terminée (agent)"""
    missions = get_missions_by_agent(str(ctx.author.id))
    if not any(m["id"] == mission_id for m in missions):
        await ctx.send("❌ Cette mission ne vous est pas assignée.")
        return
    
    if update_mission_status(mission_id, "terminée"):
        await ctx.send(f"✅ Mission #{mission_id} terminée !")
    else:
        await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="status")
async def change_status(ctx, mission_id: int, statut: str):
    """Change le statut d'une mission (en cours, terminée, annulée)"""
    if statut not in ["en cours", "terminée", "annulée"]:
        await ctx.send("❌ Statut invalide. Utilise : en cours, terminée, annulée")
        return
    
    if update_mission_status(mission_id, statut):
        await ctx.send(f"✅ Mission #{mission_id} → **{statut}**")
    else:
        await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="unassign")
async def unassign_mission(ctx, mission_id: int):
    """Retire une mission"""
    if delete_mission(mission_id):
        await ctx.send(f"✅ Mission #{mission_id} retirée")
    else:
        await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="servers")
async def list_servers(ctx):
    """Liste les serveurs où le bot est présent"""
    servers = "\n".join([f"• {g.name} ({g.id})" for g in bot.guilds])
    await ctx.send(f"📡 Serveurs :\n{servers}")

if __name__ == "__main__":
    if not config.TOKEN:
        print("❌ Token Discord manquant. Définis la variable d'environnement DISCORD_TOKEN")
    else:
        print("🚀 Démarrage du bot...")
        bot.run(config.TOKEN)
