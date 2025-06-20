import discord
from discord.ext import commands
import os
import sys
import traceback
from typing import Optional, List


class CogManager(commands.Cog):
    """Commands for managing cogs (loading, unloading, reloading)"""
    
    def __init__(self, bot):
        self.bot = bot
        self.cogs_dir = './cogs'
    
    def get_all_cogs(self) -> List[str]:
        """Get a list of all available cog names"""
        cogs = []
        for filename in os.listdir(self.cogs_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                cogs.append(filename[:-3])
        return sorted(cogs)
    
    def create_cog_embed(self, title: str, description: str, color: int = 0x3498db) -> discord.Embed:
        """Create a beautiful embed for cog-related responses"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="Cog Manager | Use !coghelp for more information")
        return embed
    
    @commands.group(name="cog", invoke_without_command=True)
    @commands.is_owner()
    async def cog(self, ctx):
        """Base command for cog management"""
        await self.show_cog_help(ctx)
    
    @commands.command(name="coghelp")
    @commands.is_owner()
    async def coghelp(self, ctx):
        """Show help for cog management commands"""
        await self.show_cog_help(ctx)
        
    async def show_cog_help(self, ctx):
        """Base command for cog management"""
        embed = self.create_cog_embed(
            "Cog Manager Help",
            "**Available Commands:**\n"
            "`!cogs` - List all available cogs\n"
            "`!cog load <name>` - Load a cog\n"
            "`!cog unload <name>` - Unload a cog\n"
            "`!cog refresh <name>` - Refresh (unload then load) a cog"
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="cogs")
    @commands.is_owner()
    async def list_cogs(self, ctx):
        """List all available cogs and their status"""
        all_cogs = self.get_all_cogs()
        loaded_cogs = [cog.split('.')[-1] for cog in self.bot.extensions.keys()]
        
        loaded = []
        unloaded = []
        
        for cog in all_cogs:
            if cog in loaded_cogs:
                loaded.append(f"✅ `{cog}`")
            else:
                unloaded.append(f"❌ `{cog}`")
        
        embed = self.create_cog_embed(
            "📚 Available Cogs",
            f"**Total Cogs:** {len(all_cogs)} | **Loaded:** {len(loaded)} | **Unloaded:** {len(unloaded)}"
        )
        
        if loaded:
            embed.add_field(name="✅ Loaded Cogs", value="\n".join(loaded), inline=False)
        
        if unloaded:
            embed.add_field(name="❌ Unloaded Cogs", value="\n".join(unloaded), inline=False)
        
        await ctx.send(embed=embed)
    
    @cog.command(name="load")
    @commands.is_owner()
    async def load_cog(self, ctx, cog_name: str):
        """Load a specific cog"""
        try:
            if not cog_name.startswith("cogs."):
                cog_name = f"cogs.{cog_name}"
            
            await self.bot.load_extension(cog_name)
            
            embed = self.create_cog_embed(
                "✅ Cog Loaded",
                f"Successfully loaded cog `{cog_name.split('.')[-1]}`",
                0x2ecc71  # Green color
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = self.create_cog_embed(
                "❌ Error Loading Cog",
                f"Failed to load cog `{cog_name.split('.')[-1]}`\n```py\n{type(e).__name__}: {str(e)}\n```",
                0xe74c3c  # Red color
            )
            await ctx.send(embed=embed)
    
    @cog.command(name="unload")
    @commands.is_owner()
    async def unload_cog(self, ctx, cog_name: str):
        """Unload a specific cog"""
        if cog_name.lower() in ["cogmanager", "cogs.cogmanager"]:
            embed = self.create_cog_embed(
                "❌ Cannot Unload",
                "You cannot unload the Cog Manager itself.",
                0xe74c3c  # Red color
            )
            return await ctx.send(embed=embed)
        
        try:
            if not cog_name.startswith("cogs."):
                cog_name = f"cogs.{cog_name}"
                
            await self.bot.unload_extension(cog_name)
            
            embed = self.create_cog_embed(
                "✅ Cog Unloaded",
                f"Successfully unloaded cog `{cog_name.split('.')[-1]}`",
                0xf39c12  # Orange color
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = self.create_cog_embed(
                "❌ Error Unloading Cog",
                f"Failed to unload cog `{cog_name.split('.')[-1]}`\n```py\n{type(e).__name__}: {str(e)}\n```",
                0xe74c3c  # Red color
            )
            await ctx.send(embed=embed)
    
    @cog.command(name="refresh")
    @commands.is_owner()
    async def refresh_cog(self, ctx, cog_name: str):
        """Refresh (unload and then load) a specific cog"""
        if cog_name.lower() in ["cogmanager", "cogs.cogmanager"]:
            embed = self.create_cog_embed(
                "❌ Cannot Refresh",
                "You cannot refresh the Cog Manager itself.",
                0xe74c3c  # Red color
            )
            return await ctx.send(embed=embed)
        
        if not cog_name.startswith("cogs."):
            cog_name = f"cogs.{cog_name}"
            
        try:
            try:
                await self.bot.unload_extension(cog_name)
            except commands.ExtensionNotLoaded:
                pass
                
            # Then load it
            await self.bot.load_extension(cog_name)
            
            embed = self.create_cog_embed(
                "✅ Cog Refreshed",
                f"Successfully refreshed cog `{cog_name.split('.')[-1]}`",
                0x3498db  # Blue color
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            error_traceback = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            
            embed = self.create_cog_embed(
                "❌ Error Refreshing Cog",
                f"Failed to refresh cog `{cog_name.split('.')[-1]}`\n```py\n{type(e).__name__}: {str(e)}\n```",
                0xe74c3c  # Red color
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CogManager(bot))
