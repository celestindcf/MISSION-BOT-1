import discord
from discord.ext import commands
import config
from utils.database import get_missions_by_agent

class AgentsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="my_missions")
    async def my_missions(self, ctx):
        missions = get_missions_by_agent(str(ctx.author.id))
        if not missions:
            await ctx.send("📭 Vous n'avez aucune mission assignée.")
            return
        
        embed = discord.Embed(
            title="📋 Mes missions",
            description=f"{ctx.author.mention}",
            color=discord.Color.gold()
        )
        for m in missions:
            embed.add_field(
                name=f"#{m['id']} - {m['title']}",
                value=f"Statut: {m['status']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="agents")
    @commands.has_role(config.ROLE_COMMANDANT)
    async def list_agents(self, ctx):
        guild = ctx.guild
        role = discord.utils.get(guild.roles, id=config.ROLE_AGENT)
        if not role:
            await ctx.send("❌ Rôle Agent introuvable.")
            return
        
        members = [m for m in guild.members if role in m.roles]
        embed = discord.Embed(title="👥 Agents disponibles", color=discord.Color.green())
        embed.description = "\n".join([f"• {m.mention}" for m in members[:20]])
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AgentsCog(bot))
