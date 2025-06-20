import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import asyncio
from typing import Optional, Literal


class NumbersCog(commands.Cog, name="Numbers"):
    """Get interesting facts about numbers using the Numbers API. This module provides commands to fetch random facts about numbers, dates, years, or math concepts. Users can specify a particular number or get random facts across different categories."""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = "http://numbersapi.com"
        self.categories = ["trivia", "math", "date", "year"]
    
    async def fetch_number_fact(self, number: Optional[int] = None, category: str = "trivia") -> str:
        """Fetch a fact about a number from the Numbers API"""
        if category not in self.categories:
            category = "trivia"
            
        url = f"{self.api_base_url}"
        
        if number is None:
            url += "/random"
        else:
            url += f"/{number}"
            
        url += f"/{category}"
        
        url += "?json"
        
        try:
            if hasattr(self.bot, 'session') and self.bot.session is not None:
                session = self.bot.session
                use_bot_session = True
            else:
                import aiohttp
                session = aiohttp.ClientSession()
                use_bot_session = False
                
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("text", "Sorry, couldn't find a fact for that number.")
                    else:
                        return f"Error: API returned status code {response.status}"
            finally:
                if not use_bot_session:
                    await session.close()
        except Exception as e:
            return f"Error fetching number fact: {str(e)}"
    
    @commands.hybrid_command(name="number", description="Get an interesting fact about a number")
    @app_commands.describe(
        number="The number to get a fact about (random if not specified)",
        category="The category of fact to get"
    )
    async def number_command(
        self, 
        ctx, 
        number: Optional[int] = None, 
        category: Literal["trivia", "math", "date", "year"] = "trivia"
    ):
        """Get an interesting fact about a number"""
        async with ctx.typing():
            fact = await self.fetch_number_fact(number, category)
            
            embed = discord.Embed(
                title=f"📊 Number Fact: {number if number is not None else 'Random'}",
                description=fact,
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Category", value=category.capitalize())
            
            embed.set_footer(text="Powered by numbersapi.com")
            
            await ctx.send(embed=embed)
    
    @app_commands.command(name="random_number_fact", description="Get a random number fact")
    @app_commands.describe(category="The category of fact to get")
    async def random_number_fact(
        self, 
        interaction: discord.Interaction,
        category: Literal["trivia", "math", "date", "year"] = "trivia"
    ):
        """Get a random number fact"""
        await interaction.response.defer()
        
        fact = await self.fetch_number_fact(None, category)
        
        embed = discord.Embed(
            title="🎲 Random Number Fact",
            description=fact,
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Category", value=category.capitalize())
        
        embed.set_footer(text="Powered by numbersapi.com")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="date_fact", description="Get a fact about a specific date")
    @app_commands.describe(
        month="Month (1-12)",
        day="Day (1-31)"
    )
    async def date_fact(
        self,
        interaction: discord.Interaction,
        month: int,
        day: int
    ):
        """Get a fact about a specific date"""
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            await interaction.response.send_message("Invalid date. Month must be 1-12 and day must be 1-31.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        url = f"{self.api_base_url}/{month}/{day}/date?json"
        
        try:
            if hasattr(self.bot, 'session') and self.bot.session is not None:
                session = self.bot.session
                use_bot_session = True
            else:
                import aiohttp
                session = aiohttp.ClientSession()
                use_bot_session = False
                
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        fact = data.get("text", "Sorry, couldn't find a fact for that date.")
                        
                        embed = discord.Embed(
                            title=f"📅 Date Fact: {month}/{day}",
                            description=fact,
                            color=discord.Color.green()
                        )
                        
                        embed.set_footer(text="Powered by numbersapi.com")
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"Error: API returned status code {response.status}")
            finally:
                if not use_bot_session:
                    await session.close()
        except Exception as e:
            await interaction.followup.send(f"Error fetching date fact: {str(e)}")
    
    @app_commands.command(name="year_fact", description="Get a fact about a specific year")
    @app_commands.describe(year="The year to get a fact about")
    async def year_fact(
        self,
        interaction: discord.Interaction,
        year: int
    ):
        """Get a fact about a specific year"""
        await interaction.response.defer()
        
        url = f"{self.api_base_url}/{year}/year?json"
        
        try:
            if hasattr(self.bot, 'session') and self.bot.session is not None:
                session = self.bot.session
                use_bot_session = True
            else:
                import aiohttp
                session = aiohttp.ClientSession()
                use_bot_session = False
                
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        fact = data.get("text", "Sorry, couldn't find a fact for that year.")
                        
                        embed = discord.Embed(
                            title=f"📜 Year Fact: {year}",
                            description=fact,
                            color=discord.Color.gold()
                        )
                        
                        embed.set_footer(text="Powered by numbersapi.com")
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"Error: API returned status code {response.status}")
            finally:
                if not use_bot_session:
                    await session.close()
        except Exception as e:
            await interaction.followup.send(f"Error fetching year fact: {str(e)}")
    
    @app_commands.command(name="math_fact", description="Get a math fact about a number")
    @app_commands.describe(number="The number to get a math fact about")
    async def math_fact(
        self,
        interaction: discord.Interaction,
        number: int
    ):
        """Get a math fact about a number"""
        await interaction.response.defer()
        
        fact = await self.fetch_number_fact(number, "math")
        
        embed = discord.Embed(
            title=f"🧮 Math Fact: {number}",
            description=fact,
            color=discord.Color.purple()
        )
        
        embed.set_footer(text="Powered by numbersapi.com")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="number_trivia", description="Get trivia about a number")
    @app_commands.describe(number="The number to get trivia about")
    async def number_trivia(
        self,
        interaction: discord.Interaction,
        number: int
    ):
        """Get trivia about a number"""
        await interaction.response.defer()
        
        fact = await self.fetch_number_fact(number, "trivia")
        
        embed = discord.Embed(
            title=f"💡 Number Trivia: {number}",
            description=fact,
            color=discord.Color.teal()
        )
        
        embed.set_footer(text="Powered by numbersapi.com")
        
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(NumbersCog(bot))
