import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import json
import re
from datetime import datetime

class Wikipedia(commands.Cog):
    """Wikipedia commands for searching and retrieving information"""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://en.wikipedia.org/api/rest_v1"
        self.wiki_url = "https://en.wikipedia.org/wiki"
        self.session = None
    
    async def cog_load(self):
        """Create aiohttp session when cog is loaded"""
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """Close aiohttp session when cog is unloaded"""
        if self.session:
            await self.session.close()
    
    @commands.command(name="wiki")
    async def wiki_search(self, ctx, *, query: str):
        """Search Wikipedia and get a summary
        
        Example: !wiki Python programming language
        """
        async with ctx.typing():
            try:
                # Search for the article
                search_results = await self._search_wikipedia(query)
                
                if not search_results:
                    await ctx.send(f"❌ No Wikipedia results found for '{query}'")
                    return
                
                # Get the first result's page title
                page_title = search_results[0]
                
                # Get the summary
                summary = await self._get_summary(page_title)
                
                if not summary:
                    await ctx.send(f"❌ Could not retrieve summary for '{page_title}'")
                    return
                
                # Create and send embed
                embed = self._create_wiki_embed(page_title, summary)
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="wikipedia", description="Search Wikipedia and get a summary")
    @app_commands.describe(query="What to search for on Wikipedia")
    async def wiki_slash(self, interaction: discord.Interaction, query: str):
        """Search Wikipedia using slash command"""
        await interaction.response.defer()
        
        try:
            # Search for the article
            search_results = await self._search_wikipedia(query)
            
            if not search_results:
                await interaction.followup.send(f"❌ No Wikipedia results found for '{query}'")
                return
            
            # Get the first result's page title
            page_title = search_results[0]
            
            # Get the summary
            summary = await self._get_summary(page_title)
            
            if not summary:
                await interaction.followup.send(f"❌ Could not retrieve summary for '{page_title}'")
                return
            
            # Create and send embed
            embed = self._create_wiki_embed(page_title, summary)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="wikilinks")
    async def wiki_links(self, ctx, *, title: str):
        """Get links from a Wikipedia article
        
        Example: !wikilinks Python programming language
        """
        async with ctx.typing():
            try:
                # Search for the article first to get the exact title
                search_results = await self._search_wikipedia(title)
                
                if not search_results:
                    await ctx.send(f"❌ No Wikipedia results found for '{title}'")
                    return
                
                # Get the first result's page title
                page_title = search_results[0]
                
                # Get links
                links = await self._get_links(page_title)
                
                if not links:
                    await ctx.send(f"❌ Could not retrieve links for '{page_title}'")
                    return
                
                # Limit to 15 links to avoid oversized messages
                links = links[:15]
                
                # Create embed
                embed = discord.Embed(
                    title=f"🔗 Links from '{page_title}'",
                    url=f"{self.wiki_url}/{page_title.replace(' ', '_')}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                # Add links as fields
                for i, link in enumerate(links, 1):
                    embed.add_field(
                        name=f"{i}. {link}",
                        value=f"[View](https://en.wikipedia.org/wiki/{link.replace(' ', '_')})",
                        inline=False
                    )
                
                embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="randomwiki")
    async def random_wiki(self, ctx):
        """Get a random Wikipedia article
        
        Example: !randomwiki
        """
        async with ctx.typing():
            try:
                # Get random article
                page_title = await self._get_random_article()
                
                if not page_title:
                    await ctx.send("❌ Could not retrieve a random article")
                    return
                
                # Get the summary
                summary = await self._get_summary(page_title)
                
                if not summary:
                    await ctx.send(f"❌ Could not retrieve summary for '{page_title}'")
                    return
                
                # Create and send embed
                embed = self._create_wiki_embed(page_title, summary)
                embed.set_author(name="🎲 Random Wikipedia Article")
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="random_wikipedia", description="Get a random Wikipedia article")
    async def random_wiki_slash(self, interaction: discord.Interaction):
        """Get a random Wikipedia article using slash command"""
        await interaction.response.defer()
        
        try:
            # Get random article
            page_title = await self._get_random_article()
            
            if not page_title:
                await interaction.followup.send("❌ Could not retrieve a random article")
                return
            
            # Get the summary
            summary = await self._get_summary(page_title)
            
            if not summary:
                await interaction.followup.send(f"❌ Could not retrieve summary for '{page_title}'")
                return
            
            # Create and send embed
            embed = self._create_wiki_embed(page_title, summary)
            embed.set_author(name="🎲 Random Wikipedia Article")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def _search_wikipedia(self, query):
        """Search Wikipedia for a query and return page titles"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5
        }
        
        async with self.session.get("https://en.wikipedia.org/w/api.php", params=params) as response:
            if response.status != 200:
                return []
                
            data = await response.json()
            
            if "query" not in data or "search" not in data["query"]:
                return []
                
            return [result["title"] for result in data["query"]["search"]]
    
    async def _get_summary(self, title):
        """Get summary of a Wikipedia article"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # URL encode the title
        encoded_title = title.replace(" ", "_")
        
        async with self.session.get(f"{self.api_url}/page/summary/{encoded_title}") as response:
            if response.status != 200:
                return None
                
            data = await response.json()
            
            # Extract the summary and clean it up
            extract = data.get("extract", "")
            
            # If the extract is too long, truncate it
            if len(extract) > 1000:
                extract = extract[:997] + "..."
                
            return {
                "title": data.get("title", title),
                "extract": extract,
                "thumbnail": data.get("thumbnail", {}).get("source") if "thumbnail" in data else None,
                "url": data.get("content_urls", {}).get("desktop", {}).get("page") if "content_urls" in data else f"{self.wiki_url}/{encoded_title}"
            }
    
    async def _get_links(self, title):
        """Get links from a Wikipedia article"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        params = {
            "action": "query",
            "titles": title,
            "prop": "links",
            "pllimit": 20,
            "format": "json"
        }
        
        async with self.session.get("https://en.wikipedia.org/w/api.php", params=params) as response:
            if response.status != 200:
                return []
                
            data = await response.json()
            
            if "query" not in data or "pages" not in data["query"]:
                return []
                
            # Get the first (and only) page
            page_id = next(iter(data["query"]["pages"]))
            page = data["query"]["pages"][page_id]
            
            if "links" not in page:
                return []
                
            return [link["title"] for link in page["links"]]
    
    async def _get_random_article(self):
        """Get a random Wikipedia article"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        params = {
            "action": "query",
            "list": "random",
            "rnnamespace": 0,  # Main namespace only
            "rnlimit": 1,
            "format": "json"
        }
        
        async with self.session.get("https://en.wikipedia.org/w/api.php", params=params) as response:
            if response.status != 200:
                return None
                
            data = await response.json()
            
            if "query" not in data or "random" not in data["query"] or not data["query"]["random"]:
                return None
                
            return data["query"]["random"][0]["title"]
    
    def _create_wiki_embed(self, title, summary_data):
        """Create a Discord embed for a Wikipedia article"""
        embed = discord.Embed(
            title=f"📚 {summary_data.get('title', title)}",
            url=summary_data.get("url", f"{self.wiki_url}/{title.replace(' ', '_')}"),
            description=summary_data.get("extract", "No summary available."),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if summary_data.get("thumbnail"):
            embed.set_thumbnail(url=summary_data["thumbnail"])
            
        embed.add_field(
            name="Read More",
            value=f"[View Full Article]({summary_data.get('url', self.wiki_url + '/' + title.replace(' ', '_'))})",
            inline=False
        )
        
        embed.set_footer(text="Source: Wikipedia", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Wikipedia's_W.svg/240px-Wikipedia's_W.svg.png")
        
        return embed

async def setup(bot):
    await bot.add_cog(Wikipedia(bot))
