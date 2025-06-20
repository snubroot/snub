import discord
from discord.ext import commands
import requests
import json
import os
from datetime import datetime
import aiohttp
import asyncio

class News(commands.Cog):
    """Real-time news fetcher commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.gnews_api_key = os.getenv("GNEWS_API_KEY", "")
        self.gnews_base_url = "https://gnews.io/api/v4"
        self.premium_users_path = "data/premium_users.json"
        self.news_feeds_path = "data/news_feeds.json"
        
        # Create premium users file if it doesn't exist
        os.makedirs(os.path.dirname(self.premium_users_path), exist_ok=True)
        if not os.path.exists(self.premium_users_path):
            with open(self.premium_users_path, "w") as f:
                json.dump([], f)
                
        # Create news feeds file if it doesn't exist
        if not os.path.exists(self.news_feeds_path):
            with open(self.news_feeds_path, "w") as f:
                json.dump({}, f)
    
    @commands.command(name="news")
    async def fetch_news(self, ctx, category=None, *, search_query=None):
        """Fetch latest news headlines by category or search term
        
        Examples: 
        !news tech
        !news crypto
        !news search "discord bots"
        """
        try:
            # Handle different command formats
            if category == "search" and search_query:
                # Search for specific query
                await self._fetch_news_by_query(ctx, search_query)
            elif category and not search_query:
                # Fetch news by category
                await self._fetch_news_by_category(ctx, category)
            else:
                # Show general top headlines
                await self._fetch_top_headlines(ctx)
                
        except Exception as e:
            await ctx.send(f"❌ Error fetching news: {str(e)}")
    
    async def _fetch_news_by_query(self, ctx, query):
        """Fetch news based on search query"""
        params = {
            "q": query,
            "lang": "en",
            "country": "us",
            "max": 5,
            "apikey": self.gnews_api_key
        }
        
        async with ctx.typing():
            articles = await self._make_gnews_request("/search", params)
            if not articles:
                await ctx.send(f"❌ No news found for query: {query}")
                return
                
            embed = self._create_news_embed(f"📰 News Results for: {query}", articles)
            await ctx.send(embed=embed)
    
    async def _fetch_news_by_category(self, ctx, category):
        """Fetch news by category"""
        # Map common category inputs to GNews categories
        category_map = {
            "tech": "technology",
            "technology": "technology",
            "business": "business",
            "entertainment": "entertainment",
            "health": "health",
            "science": "science",
            "sports": "sports",
            "crypto": "business",  # Map crypto to business as it's a common request
            "world": "world",
            "nation": "nation",
            "general": "general"
        }
        
        # Get the standardized category or default to general
        gnews_category = category_map.get(category.lower(), "general")
        
        params = {
            "category": gnews_category,
            "lang": "en",
            "country": "us",
            "max": 5,
            "apikey": self.gnews_api_key
        }
        
        async with ctx.typing():
            articles = await self._make_gnews_request("/top-headlines", params)
            if not articles:
                await ctx.send(f"❌ No news found for category: {category}")
                return
                
            embed = self._create_news_embed(f"📰 Latest {category.title()} News", articles)
            await ctx.send(embed=embed)
    
    async def _fetch_top_headlines(self, ctx):
        """Fetch top headlines"""
        params = {
            "lang": "en",
            "country": "us",
            "max": 5,
            "apikey": self.gnews_api_key
        }
        
        async with ctx.typing():
            articles = await self._make_gnews_request("/top-headlines", params)
            if not articles:
                await ctx.send("❌ Unable to fetch top headlines at this time")
                return
                
            embed = self._create_news_embed("📰 Today's Top Headlines", articles)
            await ctx.send(embed=embed)
    
    async def _make_gnews_request(self, endpoint, params):
        """Make a request to the GNews API"""
        url = f"{self.gnews_base_url}{endpoint}"
        
        if not self.gnews_api_key:
            raise ValueError("GNews API key not configured. Please add GNEWS_API_KEY to your .env file.")
        
        async with self.bot.session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"API Error ({response.status}): {error_text}")
                
            data = await response.json()
            return data.get("articles", [])
    
    def _create_news_embed(self, title, articles):
        """Create a Discord embed with news articles"""
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for i, article in enumerate(articles[:5]):  # Limit to 5 articles
            # Format the article title and description
            article_title = article.get("title", "No title")
            article_description = article.get("description", "No description available")
            source_name = article.get("source", {}).get("name", "Unknown Source")
            published_at = article.get("publishedAt", "")
            article_url = article.get("url", "")
            
            # Format the date if available
            date_str = ""
            if published_at:
                try:
                    # Parse ISO format date
                    date_obj = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    date_str = f"Published: {date_obj.strftime('%Y-%m-%d')}"
                except:
                    date_str = f"Published: {published_at}"
            
            # Add field for each article
            embed.add_field(
                name=f"📰 [{article_title}] – {source_name}",
                value=f"> \"{article_description[:100]}...\"\n{date_str}\n[Read more]({article_url})",
                inline=False
            )
        
        embed.set_footer(text="Powered by GNews.io • Type !news help for more options")
        return embed
    
    @commands.command(name="news_subscribe")
    @commands.has_permissions(administrator=True)
    async def subscribe_news(self, ctx, category, channel: discord.TextChannel = None):
        """[PREMIUM] Subscribe to daily news updates in a channel
        
        Example: !news_subscribe tech #tech-news
        """
        # Check if user is premium
        is_premium = await self._check_premium(ctx.author.id)
        if not is_premium:
            embed = discord.Embed(
                title="Premium Feature",
                description="News subscriptions are a premium feature. Contact the bot owner to upgrade.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return
        
        channel = channel or ctx.channel
        
        # Load current feeds
        feeds = {}
        if os.path.exists(self.news_feeds_path):
            with open(self.news_feeds_path, "r") as f:
                feeds = json.load(f)
        
        # Add or update feed
        guild_id = str(ctx.guild.id)
        if guild_id not in feeds:
            feeds[guild_id] = {}
            
        feeds[guild_id][category] = {
            "channel_id": channel.id,
            "last_update": datetime.now().isoformat()
        }
        
        # Save feeds
        with open(self.news_feeds_path, "w") as f:
            json.dump(feeds, f, indent=4)
            
        await ctx.send(f"✅ Successfully subscribed to {category} news in {channel.mention}!")
    
    @commands.command(name="news_unsubscribe")
    @commands.has_permissions(administrator=True)
    async def unsubscribe_news(self, ctx, category):
        """[PREMIUM] Unsubscribe from a news category
        
        Example: !news_unsubscribe tech
        """
        # Load current feeds
        if not os.path.exists(self.news_feeds_path):
            await ctx.send("❌ No news subscriptions found.")
            return
            
        with open(self.news_feeds_path, "r") as f:
            feeds = json.load(f)
        
        guild_id = str(ctx.guild.id)
        if guild_id not in feeds or category not in feeds[guild_id]:
            await ctx.send(f"❌ No subscription found for {category} news.")
            return
            
        # Remove subscription
        del feeds[guild_id][category]
        if not feeds[guild_id]:
            del feeds[guild_id]
            
        # Save feeds
        with open(self.news_feeds_path, "w") as f:
            json.dump(feeds, f, indent=4)
            
        await ctx.send(f"✅ Successfully unsubscribed from {category} news.")
    
    @commands.command(name="news_help")
    async def news_help(self, ctx):
        """Show help for news commands"""
        embed = discord.Embed(
            title="📰 News Command Help",
            description="Get the latest news headlines with these commands:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Basic Commands",
            value=(
                "`!news` - Get top headlines\n"
                "`!news tech` - Get technology news\n"
                "`!news crypto` - Get cryptocurrency news\n"
                "`!news search \"discord bots\"` - Search for specific news\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Available Categories",
            value="tech, business, entertainment, health, science, sports, crypto, world, nation, general",
            inline=False
        )
        
        embed.add_field(
            name="Premium Features",
            value=(
                "`!news_subscribe tech #channel` - Daily news updates to a channel\n"
                "`!news_unsubscribe tech` - Stop daily updates for a category\n"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _check_premium(self, user_id):
        """Check if a user has premium status"""
        if not os.path.exists(self.premium_users_path):
            return False
            
        with open(self.premium_users_path, "r") as f:
            premium_users = json.load(f)
            
        return str(user_id) in premium_users or user_id in premium_users

async def setup(bot):
    await bot.add_cog(News(bot))
