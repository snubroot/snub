import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import traceback

class Ping(commands.Cog):
    """Ping commands for checking bot latency and response time. Use these commands to verify the bot is online and responsive, and to check connection quality between the bot and Discord servers."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping_slash(self, interaction: discord.Interaction):
        """Check the bot's latency"""
        try:
            print(f"Ping command executed by {interaction.user.name}")
            latency = round(self.bot.latency * 1000)
            
            if latency < 100:
                color = discord.Color.green()
                status = "Excellent"
                emoji = "🚀"
            elif latency < 200:
                color = discord.Color.blue()
                status = "Good"
                emoji = "✅"
            elif latency < 400:
                color = discord.Color.gold()
                status = "Moderate"
                emoji = "⚠️"
            else:
                color = discord.Color.red()
                status = "Poor"
                emoji = "❌"
            
            embed = discord.Embed(
                title=f"{emoji} Ping Results",
                description=f"**Status:** {status}\n**Latency:** {latency}ms",
                color=color,
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(
                name="Bot Info", 
                value=f"Discord Latency: {latency}ms"
            )
            
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            print(f"Ping response sent with latency: {latency}ms")
        except Exception as e:
            print(f"Error in ping command: {e}")
            print(traceback.format_exc())
            try:
                await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            except:
                pass

async def setup(bot):
    await bot.add_cog(Ping(bot))
