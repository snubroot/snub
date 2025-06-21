import discord
import json
import os
import random
import asyncio
from discord.ext import commands
from openai import OpenAI
from datetime import datetime, timedelta
import config

class FortuneCog(commands.Cog):
    """Fortune cookie generator using OpenAI"""
    
    def __init__(self, bot):
        self.bot = bot
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # User cooldowns - track timestamps of last usage
        self.cooldowns = {}
        
        # Daily usage tracking
        self.daily_usage = {}
        
        # Fortune history storage
        self.history_file = "data/fortune_history.json"
        self.history = self._load_history()
        
        # Default settings
        self.cooldown_seconds = 30
        self.max_daily_uses = 10
        self.purge_days = 14  # Purge fortunes older than 14 days
        
        # Fortune personality modes
        self.modes = {
            "default": "Write a mysterious, short fortune like from a Chinese fortune cookie. It should be 1-2 sentences max. No fortune should repeat or be overly similar. Avoid clichés unless reimagined.",
            "wholesome": "Write a positive, uplifting fortune cookie message that inspires hope and joy. Keep it to 1-2 sentences max. Make it warm and encouraging.",
            "cryptic": "Write an enigmatic, puzzling fortune that leaves the reader wondering about its deeper meaning. Use mysterious language and symbolism. Keep it to 1-2 sentences max.",
            "dark": "Write a slightly ominous fortune cookie message with dark humor. Keep it to 1-2 sentences max. Make it unsettling but still somewhat amusing.",
            "cursed": "Write a deeply unsettling fortune cookie message that reads like a curse or warning. Keep it to 1-2 sentences max. Make it creepy and foreboding."
        }
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Schedule regular purging of old fortunes
        self.bot.loop.create_task(self._schedule_purge())
    
    async def _run_openai_call(self, func, *args, **kwargs):
        """Run an OpenAI API call in a thread to prevent blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: func(*args, **kwargs)
        )
    
    def _check_cooldown(self, user_id):
        """Check if a user is on cooldown."""
        # Bypass for bot owners
        if user_id in config.OWNER_IDS:
            return False
            
        if user_id not in self.cooldowns:
            return False
            
        last_used = self.cooldowns[user_id]
        elapsed = (datetime.now() - last_used).total_seconds()
        
        return elapsed < self.cooldown_seconds
    
    def _update_cooldown(self, user_id):
        """Update a user's cooldown timestamp."""
        self.cooldowns[user_id] = datetime.now()
    
    def _check_daily_limit(self, user_id):
        """Check if a user has reached their daily usage limit."""
        # Bypass for bot owners
        if user_id in config.OWNER_IDS:
            return False
            
        # Initialize if not exists
        if user_id not in self.daily_usage:
            self.daily_usage[user_id] = 0
            
        return self.daily_usage[user_id] >= self.max_daily_uses
    
    def _increment_daily_usage(self, user_id):
        """Increment a user's daily usage."""
        if user_id not in self.daily_usage:
            self.daily_usage[user_id] = 0
        self.daily_usage[user_id] += 1
    
    def _load_history(self):
        """Load fortune history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return {"fortunes": [], "last_purge": None}
        except Exception as e:
            print(f"Error loading fortune history: {str(e)}")
            return {"fortunes": [], "last_purge": None}
    
    def _save_history(self):
        """Save fortune history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Error saving fortune history: {str(e)}")
    
    def _add_fortune_to_history(self, fortune, user_id):
        """Add a fortune to the history"""
        self.history["fortunes"].append({
            "text": fortune,
            "timestamp": datetime.now().isoformat(),
            "user_id": str(user_id)
        })
        self._save_history()
    
    def _is_similar_to_recent(self, fortune):
        """Check if a fortune is similar to recently used ones"""
        # Simple check for exact matches or high similarity
        recent_fortunes = [f["text"].lower() for f in self.history["fortunes"][-30:]]
        
        # Check for exact matches
        if fortune.lower() in recent_fortunes:
            return True
            
        # Basic similarity check (could be enhanced with more sophisticated methods)
        for recent in recent_fortunes:
            # Check if more than 50% of words are the same
            fortune_words = set(fortune.lower().split())
            recent_words = set(recent.lower().split())
            
            if len(fortune_words) == 0 or len(recent_words) == 0:
                continue
                
            common_words = fortune_words.intersection(recent_words)
            similarity = len(common_words) / min(len(fortune_words), len(recent_words))
            
            if similarity > 0.5:
                return True
                
        return False
    
    async def _purge_old_fortunes(self):
        """Purge fortunes older than the specified number of days"""
        if not self.history["fortunes"]:
            return
            
        cutoff_date = datetime.now() - timedelta(days=self.purge_days)
        new_fortunes = []
        
        for fortune in self.history["fortunes"]:
            try:
                fortune_date = datetime.fromisoformat(fortune["timestamp"])
                if fortune_date > cutoff_date:
                    new_fortunes.append(fortune)
            except (ValueError, KeyError):
                # Skip entries with invalid timestamps
                continue
                
        self.history["fortunes"] = new_fortunes
        self.history["last_purge"] = datetime.now().isoformat()
        self._save_history()
        
        print(f"Purged fortune history. Removed {len(self.history['fortunes']) - len(new_fortunes)} entries.")
    
    async def _schedule_purge(self):
        """Schedule regular purging of old fortunes"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self._purge_old_fortunes()
            # Run once a day
            await asyncio.sleep(86400)  # 24 hours
    
    async def _generate_fortune(self, mode="default"):
        """Generate a fortune using OpenAI"""
        prompt = self.modes.get(mode.lower(), self.modes["default"])
        
        try:
            response = await self._run_openai_call(
                self.openai_client.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Generate a fortune cookie message."}
                ],
                max_tokens=100,
                temperature=0.9
            )
            
            fortune = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            fortune = fortune.strip('"\'')
            
            return fortune
        except Exception as e:
            print(f"Error generating fortune: {str(e)}")
            return "Your fortune is unclear at this time."
    
    @commands.command(name="fortune")
    async def fortune(self, ctx, mode: str = "default"):
        """
        Receive a mystical fortune cookie message
        
        Usage: !fortune [mode]
        Available modes: wholesome, cryptic, dark, cursed
        Example: !fortune dark
        """
        user_id = ctx.author.id
        
        # Check cooldown
        if self._check_cooldown(user_id):
            remaining = self.cooldown_seconds - int((datetime.now() - self.cooldowns[user_id]).total_seconds())
            await ctx.send(f"🕒 Please wait {remaining} seconds before requesting another fortune.")
            return
        
        # Check daily limit
        if self._check_daily_limit(user_id):
            embed = discord.Embed(
                title="❌ Daily Limit Reached",
                description=f"You've reached your daily limit of {self.max_daily_uses} fortunes.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Validate mode
        mode = mode.lower()
        if mode not in self.modes:
            mode = "default"
        
        # Send typing indicator to show the bot is processing
        async with ctx.typing():
            # Generate fortune
            fortune = await self._generate_fortune(mode)
            
            # Check if fortune is similar to recent ones
            attempts = 0
            while self._is_similar_to_recent(fortune) and attempts < 3:
                fortune = await self._generate_fortune(mode)
                attempts += 1
            
            # Update cooldown and usage
            self._update_cooldown(user_id)
            self._increment_daily_usage(user_id)
            
            # Add to history
            self._add_fortune_to_history(fortune, user_id)
            
            # Create embed response with appropriate styling based on mode
            colors = {
                "default": discord.Color.gold(),
                "wholesome": discord.Color.from_rgb(255, 182, 193),  # Light pink
                "cryptic": discord.Color.from_rgb(138, 43, 226),     # Purple
                "dark": discord.Color.from_rgb(47, 79, 79),          # Dark slate gray
                "cursed": discord.Color.from_rgb(139, 0, 0)          # Dark red
            }
            
            emojis = {
                "default": "🥠",
                "wholesome": "🌸",
                "cryptic": "🔮",
                "dark": "💀",
                "cursed": "😈"
            }
            
            embed = discord.Embed(
                title=f"{emojis.get(mode, '🥠')} Fortune Cookie",
                description=f"*{fortune}*",
                color=colors.get(mode, discord.Color.gold())
            )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            embed.timestamp = datetime.now()
            
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FortuneCog(bot))
