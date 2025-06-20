import discord
from discord.ext import commands
import datetime
import time

class Sync(commands.Cog):
    """Command syncing functionality for Discord slash commands. This module provides owner-only commands to synchronize application commands with Discord's API, ensuring that all slash commands are properly registered and available to users. Features include detailed sync reports with command counts, processing time, and command overviews."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='sync')
    @commands.is_owner()
    async def sync(self, ctx):
        """Sync slash commands with Discord"""
        start_message = await ctx.send("🔄 **Syncing commands with Discord...**")
        start_time = time.time()
        
        try:
            synced = await self.bot.tree.sync()
            end_time = time.time()
            
            embed = discord.Embed(
                title="✨ Command Sync Complete",
                description=f"Successfully synchronized **{len(synced)}** application commands with Discord.",
                color=discord.Color.brand_green(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(
                name="⏱️ Process Time",
                value=f"{(end_time - start_time):.2f} seconds",
                inline=True
            )
            
            embed.add_field(
                name="🤖 Bot Status",
                value="Ready to use",
                inline=True
            )
            
            if synced:
                command_list = "\n".join([f"• `/{cmd.name}` - {cmd.description}" for cmd in synced[:5]])
                if len(synced) > 5:
                    command_list += f"\n• ... and {len(synced) - 5} more"
                embed.add_field(
                    name="🔍 Command Overview",
                    value=command_list or "No commands synced",
                    inline=False
                )
            
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            
            await start_message.edit(content=None, embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Sync Failed",
                description="An error occurred while syncing commands with Discord.",
                color=discord.Color.brand_red(),
                timestamp=datetime.datetime.now()
            )
            
            error_embed.add_field(
                name="Error Details",
                value=f"```{str(e)}```",
                inline=False
            )
            
            error_embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            
            await start_message.edit(content=None, embed=error_embed)

async def setup(bot):
    await bot.add_cog(Sync(bot))
