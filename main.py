import discord
from discord.ext import commands
import config
import os
import json
from threading import Thread
from datetime import datetime
import aiohttp

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

# ========== CONFIGURATION DES RÔLES ==========
ROLE_CONFIG_FILE = "role_config.json"

def load_role_config():
    if not os.path.exists(ROLE_CONFIG_FILE):
        default = {
            "commandant": None,
            "capitaine": None,
            "agent": None,
            "stagiaire": None
        }
        with open(ROLE_CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(ROLE_CONFIG_FILE, "r") as f:
        return json.load(f)

def save_role_config(data):
    with open(ROLE_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

role_config = load_role_config()

# ========== FONCTIONS BASE DE DONNÉES (missions) ==========
DATA_FILE = "data/missions.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"missions": []}
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
    original_len = len(data["missions"])
    data["missions"] = [m for m in data["missions"] if m["id"] != mission_id]
    if len(data["missions"]) < original_len:
        save_data(data)
        return True
    return False

# ========== FONCTIONS PERMISSIONS ==========
OWNER_ID = 1239559463090917407  # Remplace par ton ID Discord

def has_permission(ctx, required_role):
    """Vérifie si l'utilisateur a le rôle requis ou est le propriétaire"""
    if str(ctx.author.id) == str(OWNER_ID):
        return True

    role_id = role_config.get(required_role)
    if not role_id:
        return True

    role = ctx.guild.get_role(role_id)
    if role and role in ctx.author.roles:
        return True

    return False

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

# ========== COMMANDES GÉNÉRALES ==========
@bot.command(name="ping")
async def ping(ctx):
    """Vérifie la latence du bot"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong ! Latence : {latency}ms")

@bot.command(name="servers")
async def list_servers(ctx):
    """Liste les serveurs où le bot est présent"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return
    servers = "\n".join([f"• {g.name} ({g.id})" for g in bot.guilds])
    await ctx.send(f"📡 Serveurs :\n{servers}")

# ========== COMMANDES DE GESTION DES RÔLES ==========
@bot.command(name="link_role")
async def link_role(ctx, role_key: str, role: discord.Role):
    """Lie un rôle Discord à un rôle du bot
    Utilisation: !link_role commandant @Commandant"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    if role_key not in role_config:
        await ctx.send(f"❌ Rôle `{role_key}` inexistant. Options: commandant, capitaine, agent, stagiaire")
        return

    role_config[role_key] = role.id
    save_role_config(role_config)
    await ctx.send(f"✅ Rôle `{role_key}` lié à `{role.name}` (ID: {role.id})")

@bot.command(name="unlink_role")
async def unlink_role(ctx, role_key: str):
    """Supprime la liaison d'un rôle"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    if role_key not in role_config:
        await ctx.send(f"❌ Rôle `{role_key}` inexistant.")
        return

    role_config[role_key] = None
    save_role_config(role_config)
    await ctx.send(f"✅ Rôle `{role_key}` délié")

@bot.command(name="show_roles")
async def show_roles(ctx):
    """Affiche les rôles configurés"""
    embed = discord.Embed(title="🔗 Rôles configurés", color=discord.Color.blue())
    for key, value in role_config.items():
        if value:
            role = ctx.guild.get_role(value)
            embed.add_field(name=key, value=role.mention if role else f"ID: {value} (introuvable)", inline=False)
        else:
            embed.add_field(name=key, value="❌ Non configuré", inline=False)
    await ctx.send(embed=embed)

# ========== COMMANDES DE GESTION DES MISSIONS ==========
@bot.command(name="assign")
async def assign_mission(ctx, membre: discord.Member, *, mission: str):
    """Assigne une mission à un agent"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

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
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

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
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    if delete_mission(mission_id):
        await ctx.send(f"✅ Mission #{mission_id} retirée")
    else:
        await ctx.send(f"❌ Mission #{mission_id} introuvable")

# ========== COMMANDE OVERRIDE POUR LE PROPRIÉTAIRE ==========
@bot.command(name="override")
async def add_override(ctx, user: discord.Member):
    """Ajoute toutes les permissions à un utilisateur (propriétaire uniquement)"""
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("❌ Seul le propriétaire peut utiliser cette commande.")
        return

    await ctx.send(f"✅ Override ajouté pour {user.mention}. Il a désormais toutes les permissions.")

# ========== COMMANDE CHECK BLACKLIST JUPITER ==========
JUPITER_API_URL = os.getenv("JUPITER_API_URL", "https://jupiter-network.pixelhorizons.fr")

@bot.command(name="check")
async def check_blacklist(ctx, user_id: str = None, membre: discord.Member = None):
    """Vérifie si un utilisateur est dans la blacklist Jupiter
    Utilisation: !check @membre ou !check 123456789012345678"""

    # Récupérer l'ID à vérifier
    if membre:
        user_id = str(membre.id)
    elif not user_id:
        await ctx.send("❌ Utilisation: !check @membre ou !check ID")
        return

    if not user_id.isdigit() or len(user_id) < 17:
        await ctx.send("❌ ID invalide. Utilise un ID Discord valide (17-19 chiffres).")
        return

    # Envoyer un message de chargement
    msg = await ctx.send(f"🔍 Vérification de `{user_id}`...")

    try:
        # Appeler l'API Jupiter
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{JUPITER_API_URL}/api/check/{user_id}", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("isBlacklisted"):
                        embed = discord.Embed(
                            title="🚨 Utilisateur blacklisté",
                            description=f"L'utilisateur `{user_id}` est dans la blacklist Jupiter.",
                            color=discord.Color.red()
                        )
                        embed.add_field(name="Raison", value=data.get("reason", "Non spécifiée"), inline=False)
                        embed.add_field(name="Date", value=data.get("blacklistedAt", "Inconnue"), inline=True)
                        embed.set_footer(text="Jupiter Network")
                        await msg.edit(content=None, embed=embed)
                    else:
                        embed = discord.Embed(
                            title="✅ Utilisateur non blacklisté",
                            description=f"L'utilisateur `{user_id}` n'est pas dans la blacklist Jupiter.",
                            color=discord.Color.green()
                        )
                        embed.set_footer(text="Jupiter Network")
                        await msg.edit(content=None, embed=embed)
                else:
                    await msg.edit(content=f"❌ Erreur API Jupiter: {response.status}")

    except aiohttp.ClientError:
        await msg.edit(content="❌ API Jupiter inaccessible. Vérifie que le serveur est en ligne.")
    except Exception as e:
        await msg.edit(content=f"❌ Erreur: {e}")

# ========== LANCEMENT ==========
if __name__ == "__main__":
    if not config.TOKEN:
        print("❌ Token Discord manquant. Définis la variable d'environnement DISCORD_TOKEN")
    else:
        print("🚀 Démarrage du bot...")
        bot.run(config.TOKEN)
