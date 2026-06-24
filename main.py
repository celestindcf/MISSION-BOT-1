import discord
from discord.ext import commands
import config
import os
import json
from threading import Thread
from datetime import datetime
import aiohttp
import asyncio

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
JUPITER_API_URL = os.getenv("JUPITER_API_URL", "http://5.180.34.39:27247")
JUPITER_API_KEY = os.getenv("JUPITER_API_KEY", "feellikeherjesko")

@bot.command(name="check")
async def check_blacklist(ctx, user_id: str = None, membre: discord.Member = None):
    """Vérifie si un utilisateur est dans la blacklist Jupiter
    Utilisation: !check @membre ou !check 123456789012345678"""

    if membre:
        user_id = str(membre.id)
    elif not user_id:
        await ctx.send("❌ Utilisation: !check @membre ou !check ID")
        return

    if not user_id.isdigit() or len(user_id) < 17:
        await ctx.send("❌ ID invalide. Utilise un ID Discord valide (17-19 chiffres).")
        return

    msg = await ctx.send(f"🔍 Vérification de `{user_id}`...")

    try:
        headers = {"X-API-Key": JUPITER_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{JUPITER_API_URL}/api/check/{user_id}", headers=headers, timeout=10) as response:
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
        # ========== 1. COMMANDES DE MISSION AVANCÉES ==========

@bot.command(name="accept")
async def accept_mission(ctx, mission_id: int):
    """Accepte une mission assignée et la passe en cours"""
    missions = get_missions_by_agent(str(ctx.author.id))
    if not any(m["id"] == mission_id for m in missions):
        await ctx.send("❌ Cette mission ne vous est pas assignée.")
        return

    if update_mission_status(mission_id, "en cours"):
        await ctx.send(f"✅ Mission #{mission_id} acceptée et en cours !")
    else:
        await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="decline")
async def decline_mission(ctx, mission_id: int):
    """Refuse une mission assignée"""
    missions = get_missions_by_agent(str(ctx.author.id))
    if not any(m["id"] == mission_id for m in missions):
        await ctx.send("❌ Cette mission ne vous est pas assignée.")
        return

    if update_mission_status(mission_id, "annulée"):
        await ctx.send(f"❌ Mission #{mission_id} refusée.")
    else:
        await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="priority")
async def set_priority(ctx, mission_id: int, priority: str):
    """Définit la priorité d'une mission (haute/moyenne/basse)"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    if priority not in ["haute", "moyenne", "basse"]:
        await ctx.send("❌ Priorité invalide. Utilise : haute, moyenne, basse")
        return

    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            m["priority"] = priority
            save_data(data)
            await ctx.send(f"✅ Mission #{mission_id} priorité : **{priority}**")
            return
    await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="deadline")
async def set_deadline(ctx, mission_id: int, *, date: str):
    """Ajoute une date limite à une mission (format: JJ/MM/AAAA)"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    try:
        deadline = datetime.strptime(date, "%d/%m/%Y")
    except ValueError:
        await ctx.send("❌ Format de date invalide. Utilise : JJ/MM/AAAA")
        return

    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            m["deadline"] = deadline.isoformat()
            save_data(data)
            await ctx.send(f"✅ Mission #{mission_id} date limite : **{deadline.strftime('%d/%m/%Y')}**")
            return
    await ctx.send(f"❌ Mission #{mission_id} introuvable")

@bot.command(name="overdue")
async def list_overdue(ctx):
    """Liste les missions en retard"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    now = datetime.now()
    overdue = []

    for m in data["missions"]:
        if m.get("deadline") and m["status"] not in ["terminée", "annulée"]:
            deadline = datetime.fromisoformat(m["deadline"])
            if deadline < now:
                overdue.append(m)

    if not overdue:
        await ctx.send("📭 Aucune mission en retard.")
        return

    embed = discord.Embed(
        title="⏰ Missions en retard",
        color=discord.Color.red()
    )
    for m in overdue[:10]:
        embed.add_field(
            name=f"#{m['id']} - {m['title']}",
            value=f"Deadline: {datetime.fromisoformat(m['deadline']).strftime('%d/%m/%Y')}\nAssignée à: <@{m['assigned_to']}>" if m["assigned_to"] else "Non assignée",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="history")
async def mission_history(ctx, membre: discord.Member):
    """Voir l'historique des missions d'un agent"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    missions = [m for m in data["missions"] if m.get("assigned_to") == str(membre.id)]

    if not missions:
        await ctx.send(f"📭 {membre.mention} n'a pas d'historique de missions.")
        return

    embed = discord.Embed(
        title=f"📋 Historique de {membre.display_name}",
        color=discord.Color.blue()
    )

    for m in missions[-10:]:
        embed.add_field(
            name=f"#{m['id']} - {m['title']}",
            value=f"Statut: {m['status']}",
            inline=False
        )

    embed.set_footer(text=f"Total: {len(missions)} missions")
    await ctx.send(embed=embed)

@bot.command(name="stats")
async def my_stats(ctx):
    """Voir vos statistiques personnelles"""
    data = load_data()
    missions = [m for m in data["missions"] if m.get("assigned_to") == str(ctx.author.id)]

    total = len(missions)
    en_cours = len([m for m in missions if m["status"] == "en cours"])
    terminees = len([m for m in missions if m["status"] == "terminée"])
    annulees = len([m for m in missions if m["status"] == "annulée"])

    embed = discord.Embed(
        title=f"📊 Statistiques de {ctx.author.display_name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="📋 Total missions", value=total, inline=True)
    embed.add_field(name="🔄 En cours", value=en_cours, inline=True)
    embed.add_field(name="✅ Terminées", value=terminees, inline=True)
    embed.add_field(name="❌ Annulées", value=annulees, inline=True)

    if terminees > 0:
        taux = round((terminees / total) * 100)
        embed.add_field(name="📈 Taux de réussite", value=f"{taux}%", inline=True)

    await ctx.send(embed=embed)


# ========== 2. COMMANDES BLACK OPS SPÉCIFIQUES ==========

@bot.command(name="mission_infiltrer")
async def mission_infiltrer(ctx, cible: str, membre: discord.Member):
    """Crée une mission d'infiltration"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    mission = f"INFILTRATION - {cible}"
    desc = f"Mission d'infiltration sur {cible}. Objectif: collecter des preuves et IDs."

    result = create_mission(mission, desc, str(membre.id))
    assign_mission(result["id"], str(membre.id))

    embed = discord.Embed(
        title="🕵️ Mission d'infiltration",
        description=f"**{mission}**",
        color=discord.Color.dark_gold()
    )
    embed.add_field(name="Cible", value=cible, inline=True)
    embed.add_field(name="Agent", value=membre.mention, inline=True)
    embed.add_field(name="ID", value=result["id"], inline=True)
    await ctx.send(embed=embed)

    try:
        await membre.send(f"🕵️ **Mission d'infiltration**\nCible: {cible}\nID: #{result['id']}")
    except:
        pass

@bot.command(name="mission_osint")
async def mission_osint(ctx, cible: str, membre: discord.Member):
    """Crée une mission OSINT"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    mission = f"OSINT - {cible}"
    desc = f"Mission de renseignement sur {cible}. Recueillir toutes les informations disponibles."

    result = create_mission(mission, desc, str(membre.id))
    assign_mission(result["id"], str(membre.id))

    embed = discord.Embed(
        title="🔍 Mission OSINT",
        description=f"**{mission}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Cible", value=cible, inline=True)
    embed.add_field(name="Agent", value=membre.mention, inline=True)
    embed.add_field(name="ID", value=result["id"], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="mission_forensic")
async def mission_forensic(ctx, membre: discord.Member):
    """Crée une mission forensic"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    mission = "FORENSIC - Analyse de logs"
    desc = "Analyser les logs, recouper les informations et produire un rapport."

    result = create_mission(mission, desc, str(membre.id))
    assign_mission(result["id"], str(membre.id))

    embed = discord.Embed(
        title="🔬 Mission Forensic",
        description=f"**{mission}**",
        color=discord.Color.purple()
    )
    embed.add_field(name="Agent", value=membre.mention, inline=True)
    embed.add_field(name="ID", value=result["id"], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="mission_watchdog")
async def mission_watchdog(ctx, cible: str, membre: discord.Member):
    """Crée une mission de surveillance"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    mission = f"WATCHDOG - {cible}"
    desc = f"Surveiller {cible} et alerter en cas d'activité suspecte."

    result = create_mission(mission, desc, str(membre.id))
    assign_mission(result["id"], str(membre.id))

    embed = discord.Embed(
        title="👁️ Mission Watchdog",
        description=f"**{mission}**",
        color=discord.Color.dark_teal()
    )
    embed.add_field(name="Cible", value=cible, inline=True)
    embed.add_field(name="Agent", value=membre.mention, inline=True)
    embed.add_field(name="ID", value=result["id"], inline=True)
    await ctx.send(embed=embed)


# ========== 3. NOTIFICATIONS ET ALERTES ==========

@bot.command(name="alert")
async def send_alert(ctx, role: discord.Role, *, message: str):
    """Envoie une alerte à un rôle"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    embed = discord.Embed(
        title="🚨 ALERTE",
        description=message,
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Par {ctx.author.display_name}")

    await ctx.send(f"{role.mention}", embed=embed)

@bot.command(name="broadcast")
async def broadcast_message(ctx, *, message: str):
    """Diffuse un message à tous"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    embed = discord.Embed(
        title="📢 ANNONCE",
        description=message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Par {ctx.author.display_name}")

    await ctx.send("@everyone", embed=embed)

@bot.command(name="notify")
async def notify_user(ctx, membre: discord.Member, *, message: str):
    """Envoie une notification privée à un utilisateur"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    try:
        embed = discord.Embed(
            title="📨 Notification",
            description=message,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"De {ctx.author.display_name}")

        await membre.send(embed=embed)
        await ctx.send(f"✅ Notification envoyée à {membre.mention}")
    except:
        await ctx.send(f"❌ Impossible d'envoyer un message à {membre.mention} (MP fermés).")

@bot.command(name="remind")
async def remind_mission(ctx, mission_id: int):
    """Rappelle une mission à l'agent assigné"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    mission = None
    for m in data["missions"]:
        if m["id"] == mission_id:
            mission = m
            break

    if not mission:
        await ctx.send(f"❌ Mission #{mission_id} introuvable.")
        return

    if not mission.get("assigned_to"):
        await ctx.send(f"❌ Mission #{mission_id} n'est pas assignée.")
        return

    membre = ctx.guild.get_member(int(mission["assigned_to"]))
    if not membre:
        await ctx.send("❌ Agent introuvable.")
        return

    embed = discord.Embed(
        title="⏰ Rappel de mission",
        description=f"**{mission['title']}**",
        color=discord.Color.gold()
    )
    embed.add_field(name="ID", value=mission_id, inline=True)
    embed.add_field(name="Statut", value=mission["status"], inline=True)
    embed.set_footer(text="Merci de terminer cette mission.")

    try:
        await membre.send(embed=embed)
        await ctx.send(f"✅ Rappel envoyé à {membre.mention}")
    except:
        await ctx.send(f"❌ Impossible d'envoyer un rappel à {membre.mention}.")


# ========== 4. RAPPORTS ET ANALYSES ==========

@bot.command(name="report")
async def generate_report(ctx, membre: discord.Member = None):
    """Génère un rapport des missions (tout ou pour un agent)"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()

    if membre:
        missions = [m for m in data["missions"] if m.get("assigned_to") == str(membre.id)]
        title = f"📊 Rapport de {membre.display_name}"
    else:
        missions = data["missions"]
        title = "📊 Rapport général des missions"

    if not missions:
        await ctx.send("📭 Aucune mission à rapporter.")
        return

    total = len(missions)
    en_cours = len([m for m in missions if m["status"] == "en cours"])
    terminees = len([m for m in missions if m["status"] == "terminée"])
    annulees = len([m for m in missions if m["status"] == "annulée"])
    en_attente = len([m for m in missions if m["status"] == "en attente"])

    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )
    embed.add_field(name="📋 Total", value=total, inline=True)
    embed.add_field(name="🔄 En cours", value=en_cours, inline=True)
    embed.add_field(name="✅ Terminées", value=terminees, inline=True)
    embed.add_field(name="⏳ En attente", value=en_attente, inline=True)
    embed.add_field(name="❌ Annulées", value=annulees, inline=True)

    if terminees > 0 and total > 0:
        taux = round((terminees / total) * 100)
        embed.add_field(name="📈 Taux de réussite", value=f"{taux}%", inline=True)

    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    """Classement des agents par missions terminées"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()

    # Compter les missions terminées par agent
    counts = {}
    for m in data["missions"]:
        if m["status"] == "terminée" and m.get("assigned_to"):
            agent_id = m["assigned_to"]
            counts[agent_id] = counts.get(agent_id, 0) + 1

    if not counts:
        await ctx.send("📭 Aucune mission terminée.")
        return

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Classement des agents",
        color=discord.Color.gold()
    )

    for i, (agent_id, count) in enumerate(sorted_counts[:10], 1):
        member = ctx.guild.get_member(int(agent_id))
        name = member.display_name if member else f"ID: {agent_id}"
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        embed.add_field(
            name=f"{medal} {name}",
            value=f"{count} missions terminées",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name="export")
async def export_missions(ctx):
    """Exporte toutes les missions en CSV"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()

    if not data["missions"]:
        await ctx.send("📭 Aucune mission à exporter.")
        return

    csv = "ID,Titre,Statut,Assigné à,Date création\n"
    for m in data["missions"]:
        csv += f"{m['id']},{m['title']},{m['status']},{m.get('assigned_to', 'Non assigné')},{m['created_at'][:10]}\n"

    # Créer un fichier
    filename = f"missions_export_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(filename, "w") as f:
        f.write(csv)

    await ctx.send(file=discord.File(filename))

    # Nettoyer
    os.remove(filename)


# ========== 7. COMMANDES SMART ==========

@bot.command(name="quick")
async def quick_mission(ctx, *, mission: str):
    """Crée une mission rapide (sans assignation)"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    result = create_mission(mission, f"Mission rapide créée par {ctx.author.display_name}", None)

    embed = discord.Embed(
        title="⚡ Mission rapide créée",
        description=f"**{mission}**",
        color=discord.Color.green()
    )
    embed.add_field(name="ID", value=result["id"], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="duplicate")
async def duplicate_mission(ctx, mission_id: int):
    """Duplique une mission existante"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    original = None
    for m in data["missions"]:
        if m["id"] == mission_id:
            original = m
            break

    if not original:
        await ctx.send(f"❌ Mission #{mission_id} introuvable.")
        return

    new_mission = create_mission(
        f"{original['title']} (copie)",
        f"Copie de la mission #{mission_id}",
        original.get("assigned_to")
    )

    embed = discord.Embed(
        title="📋 Mission dupliquée",
        description=f"Nouvelle mission: **{new_mission['title']}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="ID original", value=mission_id, inline=True)
    embed.add_field(name="Nouvel ID", value=new_mission["id"], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="archive")
async def archive_mission(ctx, mission_id: int):
    """Archive une mission terminée"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            if m["status"] != "terminée":
                await ctx.send("❌ Seules les missions terminées peuvent être archivées.")
                return
            m["status"] = "archivée"
            save_data(data)
            await ctx.send(f"✅ Mission #{mission_id} archivée.")
            return
    await ctx.send(f"❌ Mission #{mission_id} introuvable.")


# ========== 8. ORGANISATION ==========

@bot.command(name="tag")
async def add_tag(ctx, mission_id: int, *, tag: str):
    """Ajoute un tag à une mission"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            if "tags" not in m:
                m["tags"] = []
            if tag not in m["tags"]:
                m["tags"].append(tag)
                save_data(data)
                await ctx.send(f"✅ Tag `{tag}` ajouté à la mission #{mission_id}")
            else:
                await ctx.send(f"ℹ️ Tag `{tag}` déjà présent")
            return
    await ctx.send(f"❌ Mission #{mission_id} introuvable.")

@bot.command(name="filter")
async def filter_by_tag(ctx, *, tag: str):
    """Filtre les missions par tag"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return

    data = load_data()
    filtered = [m for m in data["missions"] if tag in m.get("tags", [])]

    if not filtered:
        await ctx.send(f"📭 Aucune mission avec le tag `{tag}`.")
        return

    embed = discord.Embed(
        title=f"🏷️ Missions avec le tag `{tag}`",
        color=discord.Color.blue()
    )

    for m in filtered[:10]:
        embed.add_field(
            name=f"#{m['id']} - {m['title']}",
            value=f"Statut: {m['status']}",
            inline=False
        )

    await ctx.send(embed=embed)
    # ========== DEMANDE D'ACTION ET VALIDATION ==========

@bot.command(name="request_action")
async def request_action(ctx, mission_id: int, *, plan: str):
    """Demande à agir sur une mission
    Utilisation: !request_action ID "Plan d'action" """
    
    missions = get_missions_by_agent(str(ctx.author.id))
    if not any(m["id"] == mission_id for m in missions):
        await ctx.send("❌ Cette mission ne vous est pas assignée.")
        return
    
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            if m["status"] != "en cours":
                await ctx.send("❌ La mission doit être en cours pour demander une action.")
                return
            m["pending_action"] = {
                "requester": str(ctx.author.id),
                "plan": plan,
                "requested_at": datetime.now().isoformat()
            }
            save_data(data)
            
            embed = discord.Embed(
                title="📨 Demande d'action",
                description=f"**{m['title']}**",
                color=discord.Color.orange()
            )
            embed.add_field(name="Mission ID", value=mission_id, inline=True)
            embed.add_field(name="Agent", value=ctx.author.mention, inline=True)
            embed.add_field(name="Plan d'action", value=plan, inline=False)
            embed.set_footer(text="En attente de validation")
            
            await ctx.send(embed=embed)
            
            # Notifier les commandants
            for member in ctx.guild.members:
                if has_permission(ctx, "commandant"):
                    try:
                        await member.send(f"📨 Nouvelle demande d'action sur la mission #{mission_id}\n{plan[:50]}...")
                    except:
                        pass
            return
    
    await ctx.send(f"❌ Mission #{mission_id} introuvable.")

@bot.command(name="pending")
async def list_pending_requests(ctx):
    """Liste les demandes d'action en attente"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return
    
    data = load_data()
    pending = []
    for m in data["missions"]:
        if m.get("pending_action"):
            pending.append(m)
    
    if not pending:
        await ctx.send("📭 Aucune demande en attente.")
        return
    
    embed = discord.Embed(
        title="📋 Demandes en attente",
        color=discord.Color.orange()
    )
    
    for m in pending[:10]:
        action = m["pending_action"]
        embed.add_field(
            name=f"#{m['id']} - {m['title']}",
            value=f"Agent: <@{action['requester']}>\nPlan: {action['plan'][:60]}...",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="validate")
async def validate_request(ctx, mission_id: int):
    """Valide une demande d'action (commandant uniquement)"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return
    
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            if not m.get("pending_action"):
                await ctx.send(f"❌ Aucune demande en attente sur la mission #{mission_id}.")
                return
            
            requester = m["pending_action"]["requester"]
            plan = m["pending_action"]["plan"]
            
            # Supprimer la demande
            del m["pending_action"]
            save_data(data)
            
            embed = discord.Embed(
                title="✅ Demande validée",
                description=f"Mission #{mission_id}: **{m['title']}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Validé par", value=ctx.author.mention, inline=True)
            embed.add_field(name="Plan validé", value=plan, inline=False)
            
            await ctx.send(embed=embed)
            
            # Notifier l'agent
            agent = ctx.guild.get_member(int(requester))
            if agent:
                try:
                    await agent.send(f"✅ Votre demande sur la mission #{mission_id} a été validée par {ctx.author.display_name}.")
                except:
                    pass
            return
    
    await ctx.send(f"❌ Mission #{mission_id} introuvable.")

@bot.command(name="reject")
async def reject_request(ctx, mission_id: int, *, raison: str):
    """Refuse une demande d'action (commandant uniquement)"""
    if not has_permission(ctx, "commandant"):
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return
    
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            if not m.get("pending_action"):
                await ctx.send(f"❌ Aucune demande en attente sur la mission #{mission_id}.")
                return
            
            requester = m["pending_action"]["requester"]
            plan = m["pending_action"]["plan"]
            
            # Supprimer la demande
            del m["pending_action"]
            save_data(data)
            
            embed = discord.Embed(
                title="❌ Demande refusée",
                description=f"Mission #{mission_id}: **{m['title']}**",
                color=discord.Color.red()
            )
            embed.add_field(name="Refusé par", value=ctx.author.mention, inline=True)
            embed.add_field(name="Raison", value=raison, inline=False)
            
            await ctx.send(embed=embed)
            
            # Notifier l'agent
            agent = ctx.guild.get_member(int(requester))
            if agent:
                try:
                    await agent.send(f"❌ Votre demande sur la mission #{mission_id} a été refusée.\nRaison: {raison}")
                except:
                    pass
            return
    
    await ctx.send(f"❌ Mission #{mission_id} introuvable.")
    
# ========== COMMANDE D'AUTO-DESTRUCTION ==========
@bot.command(name="destroy")
async def self_destruct(ctx):
    """💣 Auto-destruction du serveur - Supprime tout et kick tout le monde"""
    
    # Seul le propriétaire peut l'utiliser
    if ctx.author.id != 1239559463090917407:
        await ctx.send("❌ Seul le propriétaire peut utiliser cette commande.")
        return
    
    # Message de confirmation avec MORI
    await ctx.send("⚠️ **DESTRUCTION IMMINENTE** ⚠️\nTape `MORI` dans 15 secondes.")
    
    def check(m):
        return m.author == ctx.author and m.content == "MORI"
    
    try:
        await bot.wait_for('message', timeout=15.0, check=check)
    except:
        await ctx.send("⏱️ Annulé.")
        return
    
    guild = ctx.guild
    msg = await ctx.send("💣 DESTRUCTION EN COURS...")
    
    # 1. Envoyer MEMENTO MORI
    await ctx.send("**MEMENTO MORI**")
    await asyncio.sleep(1)
    
    # 2. Supprimer tous les salons
    for channel in guild.channels:
        try:
            await channel.delete()
        except:
            pass
    
    # 3. Supprimer tous les rôles
    for role in guild.roles:
        if role.name != "@everyone":
            try:
                await role.delete()
            except:
                pass
    
    # 4. Kick tous les membres sauf le bot et le propriétaire
    for member in guild.members:
        if not member.bot and member.id != ctx.author.id:
            try:
                await member.kick(reason="Auto-destruction")
            except:
                pass
    
    await msg.edit(content="💣 **DESTRUCTION TERMINÉE.**")
    
    # Le bot quitte le serveur
    await guild.leave()
    
# ========== LANCEMENT ==========
if __name__ == "__main__":
    if not config.TOKEN:
        print("❌ Token Discord manquant. Définis la variable d'environnement DISCORD_TOKEN")
    else:
        print("🚀 Démarrage du bot...")
        bot.run(config.TOKEN)
