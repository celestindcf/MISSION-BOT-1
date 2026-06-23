import discord
from discord.ext import commands
import config
from utils.database import get_all_missions, update_mission_status

class MissionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="list")
    async def list_missions(self, ctx):
        data = get_all_missions()
        if not data:
            await ctx.send("📭 Aucune mission.")
            return
        
        embed = discord.Embed(title="📋 Missions", color=discord.Color.blue())
        for m in data[-10:]:
            embed.add_field(
                name=f"#{m['id']} - {m['title']}",
                value=f"Statut: {m['status']}\nAgent: <@{m['assigned_to']}>" if m["assigned_to"] else "Non assignée",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="complete")
    @commands.has_role(config.ROLE_AGENT)
    async def complete_mission(self, ctx, mission_id: int):
        if update_mission_status(mission_id, "terminée"):
            await ctx.send(f"✅ Mission #{mission_id} terminée !")
        else:
            await ctx.send(f"❌ Mission #{mission_id} introuvable")

async def setup(bot):
    await bot.add_cog(MissionsCog(bot))
