import discord
from discord.ext import commands
import config
from utils.database import create_mission, assign_mission, get_all_missions

class DispatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="assign")
    @commands.has_role(config.ROLE_COMMANDANT)
    async def assign_mission(self, ctx, membre: discord.Member, *, mission: str):
        result = create_mission(mission, f"Assignée par {ctx.author.display_name}", str(membre.id))
        assign_mission(result["id"], str(membre.id))
        
        embed = discord.Embed(
            title="📨 Mission assignée",
            description=f"**{mission}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Agent", value=membre.mention, inline=True)
        embed.add_field(name="ID", value=result["id"], inline=True)
        await ctx.send(embed=embed)
        await membre.send(f"📨 Nouvelle mission : **{mission}**")

async def setup(bot):
    await bot.add_cog(DispatchCog(bot))
