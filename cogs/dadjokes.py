import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import asyncio
from typing import Optional, Literal


class DadJokes(commands.Cog):
    """Dad jokes commands using the icanhazdadjoke API"""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://icanhazdadjoke.com/"
    
    async def fetch_dad_joke(self, joke_id: Optional[str] = None) -> dict:
        """Fetch a dad joke from the icanhazdadjoke API"""
        url = self.api_url
        
        if joke_id:
            url += f"j/{joke_id}"
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Snub Discord Bot (https://github.com/yourusername/Snub)"
        }
        
        try:
            if hasattr(self.bot, 'session') and self.bot.session is not None:
                session = self.bot.session
                use_bot_session = True
            else:
                session = aiohttp.ClientSession()
                use_bot_session = False
                
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return {"status": response.status, "joke": f"Error: API returned status code {response.status}"}
            finally:
                if not use_bot_session:
                    await session.close()
        except Exception as e:
            return {"status": 500, "joke": f"Error fetching joke: {str(e)}"}
    
    async def search_dad_jokes(self, term: str, limit: int = 5) -> list:
        """Search for dad jokes containing a specific term"""
        url = f"{self.api_url}search"
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Snub Discord Bot (https://github.com/yourusername/Snub)"
        }
        
        params = {
            "term": term,
            "limit": min(limit, 30)  # API limit is 30
        }
        
        try:
            if hasattr(self.bot, 'session') and self.bot.session is not None:
                session = self.bot.session
                use_bot_session = True
            else:
                session = aiohttp.ClientSession()
                use_bot_session = False
                
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("results", [])
                    else:
                        return []
            finally:
                if not use_bot_session:
                    await session.close()
        except Exception as e:
            return []
    
    @commands.hybrid_command(name="dadjoke", description="Get a random dad joke")
    async def dad_joke_command(self, ctx):
        """Get a random dad joke"""
        async with ctx.typing():
            joke_data = await self.fetch_dad_joke()
            
            if joke_data.get("status") == 200:
                joke = joke_data.get("joke", "No joke found")
                joke_id = joke_data.get("id", "unknown")
                
                embed = discord.Embed(
                    title="👨 Dad Joke",
                    description=joke,
                    color=discord.Color.orange()
                )
                
                embed.set_footer(text=f"Joke ID: {joke_id} • Powered by icanhazdadjoke.com")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {joke_data.get('joke', 'Failed to fetch a dad joke')}")
    
    @app_commands.command(name="random_dad_joke", description="Get a random dad joke")
    async def random_dad_joke(self, interaction: discord.Interaction):
        """Get a random dad joke using slash command"""
        await interaction.response.defer()
        
        joke_data = await self.fetch_dad_joke()
        
        if joke_data.get("status") == 200:
            joke = joke_data.get("joke", "No joke found")
            joke_id = joke_data.get("id", "unknown")
            
            embed = discord.Embed(
                title="👨 Dad Joke",
                description=joke,
                color=discord.Color.orange()
            )
            
            embed.set_footer(text=f"Joke ID: {joke_id} • Powered by icanhazdadjoke.com")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Error: {joke_data.get('joke', 'Failed to fetch a dad joke')}")
    
    @commands.hybrid_command(name="searchdadjoke", description="Search for dad jokes containing a term")
    @app_commands.describe(
        term="The term to search for in dad jokes",
        limit="Maximum number of jokes to return (default: 5, max: 30)"
    )
    async def search_dad_joke_command(self, ctx, term: str, limit: Optional[int] = 5):
        """Search for dad jokes containing a specific term"""
        if not term:
            await ctx.send("❌ Please provide a search term")
            return
            
        async with ctx.typing():
            jokes = await self.search_dad_jokes(term, limit)
            
            if not jokes:
                await ctx.send(f"❌ No dad jokes found containing '{term}'")
                return
                
            embed = discord.Embed(
                title=f"🔍 Dad Jokes Search: '{term}'",
                description=f"Found {len(jokes)} jokes containing '{term}'",
                color=discord.Color.orange()
            )
            
            for i, joke_data in enumerate(jokes[:min(limit, 10)], 1):
                joke = joke_data.get("joke", "No joke found")
                joke_id = joke_data.get("id", "unknown")
                embed.add_field(
                    name=f"Joke #{i}",
                    value=f"{joke}\n*ID: {joke_id}*",
                    inline=False
                )
            
            embed.set_footer(text="Powered by icanhazdadjoke.com")
            
            await ctx.send(embed=embed)
    
    @app_commands.command(name="search_dad_jokes", description="Search for dad jokes containing a term")
    @app_commands.describe(
        term="The term to search for in dad jokes",
        limit="Maximum number of jokes to return (default: 5, max: 30)"
    )
    async def search_dad_jokes_slash(self, interaction: discord.Interaction, term: str, limit: Optional[int] = 5):
        """Search for dad jokes containing a specific term using slash command"""
        await interaction.response.defer()
        
        if not term:
            await interaction.followup.send("❌ Please provide a search term")
            return
            
        jokes = await self.search_dad_jokes(term, limit)
        
        if not jokes:
            await interaction.followup.send(f"❌ No dad jokes found containing '{term}'")
            return
            
        embed = discord.Embed(
            title=f"🔍 Dad Jokes Search: '{term}'",
            description=f"Found {len(jokes)} jokes containing '{term}'",
            color=discord.Color.orange()
        )
        
        for i, joke_data in enumerate(jokes[:min(limit, 10)], 1):
            joke = joke_data.get("joke", "No joke found")
            joke_id = joke_data.get("id", "unknown")
            embed.add_field(
                name=f"Joke #{i}",
                value=f"{joke}\n*ID: {joke_id}*",
                inline=False
            )
        
        embed.set_footer(text="Powered by icanhazdadjoke.com")
        
        await interaction.followup.send(embed=embed)
    
    @commands.hybrid_command(name="dadjoke_help", description="Show help for dad joke commands")
    async def dad_joke_help(self, ctx):
        """Show help for dad joke commands"""
        embed = discord.Embed(
            title="👨 Dad Jokes Help",
            description="Commands for getting dad jokes from icanhazdadjoke.com",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="!dadjoke",
            value="Get a random dad joke",
            inline=False
        )
        
        embed.add_field(
            name="!searchdadjoke <term> [limit]",
            value="Search for dad jokes containing a specific term",
            inline=False
        )
        
        embed.add_field(
            name="Slash Commands",
            value="/random_dad_joke - Get a random dad joke\n/search_dad_jokes - Search for dad jokes",
            inline=False
        )
        
        embed.set_footer(text="Powered by icanhazdadjoke.com")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DadJokes(bot))
