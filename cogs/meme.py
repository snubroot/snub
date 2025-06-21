import discord
import asyncio
import aiohttp
import random
import json
from discord.ext import commands, tasks
from datetime import datetime
import config

class MemeCog(commands.Cog):
    """Reddit meme fetcher for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session if hasattr(bot, 'session') else None
        
        # If bot doesn't have a session, create one
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        # Default subreddits for different categories
        self.subreddits = {
            'random': ['memes', 'dankmemes', 'funny', 'wholesomememes', 'me_irl'],
            'dank': ['dankmemes', 'dankruto', 'PrequelMemes', 'surrealmemes'],
            'wholesome': ['wholesomememes', 'MadeMeSmile', 'wholesomeanimemes'],
            'anime': ['Animemes', 'anime_irl', 'wholesomeanimemes'],
            'gaming': ['gaming', 'gamingmemes', 'pcmasterrace'],
            'programming': ['ProgrammerHumor', 'programmerreactions', 'linuxmemes']
        }
        
        # Store active automeme tasks
        self.automeme_tasks = {}
        
        # Cooldown tracking
        self.cooldowns = {}
        self.cooldown_seconds = 5
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        # Cancel all automeme tasks
        for task in self.automeme_tasks.values():
            task.cancel()
    
    async def fetch_memes(self, subreddit, limit=25):
        """Fetch memes from a subreddit"""
        try:
            headers = {'User-Agent': 'SnubBot/1.0'}
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                posts = data['data']['children']
                
                # Filter for image posts only and remove stickied posts
                valid_posts = []
                for post in posts:
                    post_data = post['data']
                    
                    # Skip stickied posts, NSFW posts, and non-image posts
                    if post_data['stickied'] or post_data['over_18']:
                        continue
                    
                    url = post_data['url']
                    if url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        valid_posts.append({
                            'title': post_data['title'],
                            'url': url,
                            'permalink': f"https://reddit.com{post_data['permalink']}",
                            'author': post_data['author'],
                            'score': post_data['score'],
                            'num_comments': post_data['num_comments'],
                            'created_utc': post_data['created_utc']
                        })
                
                return valid_posts
        except Exception as e:
            print(f"Error fetching memes from r/{subreddit}: {str(e)}")
            return None
    
    def _check_cooldown(self, user_id):
        """Check if a user is on cooldown"""
        # Bypass for bot owners
        if user_id in config.OWNER_IDS:
            return False
            
        if user_id not in self.cooldowns:
            return False
            
        last_used = self.cooldowns[user_id]
        elapsed = (datetime.now() - last_used).total_seconds()
        
        return elapsed < self.cooldown_seconds
    
    def _update_cooldown(self, user_id):
        """Update a user's cooldown timestamp"""
        self.cooldowns[user_id] = datetime.now()
    
    async def send_meme(self, ctx, category='random', count=1):
        """Send memes to a channel"""
        # Validate count
        count = max(1, min(5, count))  # Limit between 1 and 5
        
        # Get appropriate subreddits
        subreddits = self.subreddits.get(category.lower(), self.subreddits['random'])
        
        # Choose a random subreddit
        subreddit = random.choice(subreddits)
        
        # Fetch memes
        memes = await self.fetch_memes(subreddit)
        
        if not memes or len(memes) == 0:
            await ctx.send(f"Couldn't fetch memes from r/{subreddit}. Try again later.")
            return False
        
        # Shuffle and select the requested number of memes
        random.shuffle(memes)
        selected_memes = memes[:count]
        
        for meme in selected_memes:
            embed = discord.Embed(
                title=meme['title'],
                url=meme['permalink'],
                color=discord.Color.random()
            )
            embed.set_image(url=meme['url'])
            embed.set_footer(text=f"👍 {meme['score']} | 💬 {meme['num_comments']} | Posted by u/{meme['author']}")
            
            await ctx.send(embed=embed)
            
            # Add a small delay between multiple memes to avoid rate limiting
            if count > 1:
                await asyncio.sleep(1)
        
        return True
    
    async def automeme_task(self, channel_id, category, interval):
        """Background task for automeme functionality"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
            
        while True:
            try:
                await self.send_meme(channel, category, 1)
                await asyncio.sleep(interval * 60)  # Convert minutes to seconds
            except Exception as e:
                print(f"Error in automeme task: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    @commands.command(name="meme")
    async def meme(self, ctx, category_or_count=None, count=None):
        """
        Fetch memes from Reddit
        
        Usage:
        !meme - Get a random meme
        !meme <1-5> - Get multiple random memes
        !meme <category> - Get a meme from a specific category
        !meme <category> <1-5> - Get multiple memes from a specific category
        
        Available categories: dank, wholesome, anime, gaming, programming
        """
        user_id = ctx.author.id
        
        # Check cooldown
        if self._check_cooldown(user_id):
            remaining = self.cooldown_seconds - int((datetime.now() - self.cooldowns[user_id]).total_seconds())
            await ctx.send(f"🕒 Please wait {remaining} seconds before requesting more memes.")
            return
        
        # Update cooldown
        self._update_cooldown(user_id)
        
        # Parse arguments
        category = 'random'
        meme_count = 1
        
        if category_or_count is not None:
            # Check if it's a number
            if category_or_count.isdigit():
                meme_count = int(category_or_count)
                # Ensure count is between 1 and 5
                meme_count = max(1, min(5, meme_count))
            else:
                # It's a category
                category = category_or_count.lower()
                
                # If count is also provided
                if count is not None and count.isdigit():
                    meme_count = int(count)
                    # Ensure count is between 1 and 5
                    meme_count = max(1, min(5, meme_count))
        
        # Check if category exists
        if category not in self.subreddits:
            await ctx.send(f"Unknown category: {category}. Available categories: {', '.join(self.subreddits.keys())}")
            return
        
        # Send typing indicator
        async with ctx.typing():
            await self.send_meme(ctx, category, meme_count)
    
    @commands.command(name="automeme")
    @commands.has_permissions(manage_messages=True)
    async def automeme(self, ctx, category=None, interval=None):
        """
        Automatically post memes at regular intervals
        
        Usage:
        !automeme - Start posting random memes every 30 minutes
        !automeme <category> - Start posting memes from a category every 30 minutes
        !automeme <category> <interval> - Start posting memes from a category at specified interval (in minutes)
        !automeme stop - Stop automatic meme posting in this channel
        
        Available categories: dank, wholesome, anime, gaming, programming
        Interval: Time in minutes between memes (5-60)
        """
        channel_id = ctx.channel.id
        
        # Check if user wants to stop automeme
        if category and category.lower() == 'stop':
            if channel_id in self.automeme_tasks:
                self.automeme_tasks[channel_id].cancel()
                del self.automeme_tasks[channel_id]
                await ctx.send("🛑 Automatic meme posting has been stopped in this channel.")
            else:
                await ctx.send("❌ There is no active automeme in this channel.")
            return
        
        # Check if automeme is already running in this channel
        if channel_id in self.automeme_tasks:
            await ctx.send("❌ Automeme is already running in this channel. Use `!automeme stop` to stop it first.")
            return
        
        # Set defaults
        if category is None or category.lower() not in self.subreddits:
            if category is not None and category.isdigit() and interval is None:
                # User provided interval as first argument
                interval = category
                category = 'random'
            else:
                category = 'random'
        else:
            category = category.lower()
        
        # Parse interval
        if interval is None:
            interval = 30  # Default: 30 minutes
        else:
            try:
                interval = int(interval)
                # Ensure interval is between 5 and 60 minutes
                interval = max(5, min(60, interval))
            except ValueError:
                await ctx.send("❌ Interval must be a number between 5 and 60 (minutes).")
                return
        
        # Create and start the automeme task
        task = self.bot.loop.create_task(self.automeme_task(channel_id, category, interval))
        self.automeme_tasks[channel_id] = task
        
        await ctx.send(f"✅ Automeme started! Posting {category} memes every {interval} minutes.")
    
    @automeme.error
    async def automeme_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need the 'Manage Messages' permission to use the automeme command.")

async def setup(bot):
    await bot.add_cog(MemeCog(bot))
