import discord
from discord.ext import commands
from utils.roles_manager import RolesManager
import config

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_manager = RolesManager(bot)

    @commands.command(name="config_show")
    async def show_config(self, ctx):
        if not await self.is_authorized(ctx.author):
            await ctx.send("❌ Non autorisé.")
            return
        cfg = self.roles_manager.config
        embed = discord.Embed(title="⚙️ Configuration", color=discord.Color.blue())
        roles_text = ""
        for key, data in cfg["roles"].items():
            name = data.get("name", key)
            role_id = data.get("id")
            roles_text += f"`{name}` (ID: {role_id or '❌'})\n"
        embed.add_field(name="📋 Rôles", value=roles_text or "Aucun", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="role_rename")
    async def rename_role(self, ctx, role_key: str, *, new_name: str):
        if not await self.is_authorized(ctx.author):
            await ctx.send("❌ Non autorisé.")
            return
        if role_key not in self.roles_manager.config["roles"]:
            await ctx.send(f"❌ Rôle `{role_key}` inexistant.")
            return
        await self.roles_manager.update_role_name(role_key, new_name)
        await ctx.send(f"✅ Rôle `{role_key}` renommé en `{new_name}`")

    @commands.command(name="role_link")
    async def link_role(self, ctx, role_key: str, role: discord.Role):
        if not await self.is_authorized(ctx.author):
            await ctx.send("❌ Non autorisé.")
            return
        if role_key not in self.roles_manager.config["roles"]:
            await ctx.send(f"❌ Rôle `{role_key}` inexistant.")
            return
        await self.roles_manager.update_role_id(role_key, role.id)
        await ctx.send(f"✅ `{role_key}` lié à `{role.name}`")

    @commands.command(name="user_override")
    async def add_override(self, ctx, user: discord.Member, roles: str = "", permissions: str = ""):
        if not await self.is_authorized(ctx.author):
            await ctx.send("❌ Non autorisé.")
            return
        roles_list = [r.strip() for r in roles.split(",")] if roles else []
        perms_list = [p.strip() for p in permissions.split(",")] if permissions else []
        await self.roles_manager.add_override(user.id, roles_list, perms_list)
        await ctx.send(f"✅ Override ajouté pour {user.mention}")

    @commands.command(name="user_remove")
    async def remove_override(self, ctx, user: discord.Member):
        if not await self.is_authorized(ctx.author):
            await ctx.send("❌ Non autorisé.")
            return
        await self.roles_manager.remove_override(user.id)
        await ctx.send(f"✅ Override supprimé pour {user.mention}")

    @commands.command(name="perms_list")
    async def list_perms(self, ctx):
        perms = {
            "assign": "📨 Assigner",
            "status": "📊 Statut",
            "missions": "📋 Voir toutes",
            "my_missions": "📋 Mes missions",
            "complete": "✅ Terminer",
            "agents": "👥 Liste agents",
            "agent_info": "ℹ️ Infos agent",
            "config_show": "⚙️ Config",
            "role_rename": "✏️ Renommer",
            "role_link": "🔗 Lier",
            "user_override": "👤 Override",
            "user_remove": "🗑️ Supprimer"
        }
        embed = discord.Embed(title="📋 Permissions", color=discord.Color.gold())
        for cmd, desc in perms.items():
            embed.add_field(name=f"`{cmd}`", value=desc, inline=True)
        await ctx.send(embed=embed)

    async def is_authorized(self, user):
        cfg = self.roles_manager.config
        if str(user.id) in cfg.get("overrides", {}):
            if "commandant" in cfg["overrides"][str(user.id)].get("roles", []):
                return True
        role_id = cfg["roles"].get("commandant", {}).get("id")
        if role_id:
            role = discord.utils.get(user.guild.roles, id=role_id)
            if role and role in user.roles:
                return True
        return False

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
