import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import io
import asyncio
from datetime import datetime
from typing import Optional, Literal

class DeepAI(commands.Cog):
    """DeepAI integration for various AI models and capabilities"""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("DEEPAI_API_KEY", "")
        self.api_url = "https://api.deepai.org/api/"
        self.cooldowns = {}
        self.cooldown_seconds = 10
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
    
    async def _call_deepai_api(self, endpoint, **params):
        """Make a call to the DeepAI API"""
        url = f"{self.api_url}{endpoint}"
        
        headers = {
            "api-key": self.api_key,
            "User-Agent": "Snub Discord Bot"
        }
        
        try:
            if hasattr(self.bot, 'session') and self.bot.session is not None:
                session = self.bot.session
                use_bot_session = True
            else:
                session = aiohttp.ClientSession()
                use_bot_session = False
                
            try:
                async with session.post(url, headers=headers, data=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"API returned status code {response.status}"}
            finally:
                if not use_bot_session:
                    await session.close()
        except Exception as e:
            return {"error": f"Error calling DeepAI API: {str(e)}"}
    
    def _check_cooldown(self, user_id):
        """Check if a user is on cooldown"""
        if user_id not in self.cooldowns:
            return False
            
        last_used = self.cooldowns[user_id]
        elapsed = (datetime.now() - last_used).total_seconds()
        
        return elapsed < self.cooldown_seconds
    
    def _update_cooldown(self, user_id):
        """Update a user's cooldown timestamp"""
        self.cooldowns[user_id] = datetime.now()
    
    @commands.group(name="deepai", aliases=["dai"], invoke_without_command=True)
    async def deepai_group(self, ctx):
        """DeepAI commands for various AI models"""
        await self.deepai_help(ctx)
    
    @deepai_group.command(name="help")
    async def deepai_help(self, ctx):
        """Show help for DeepAI commands"""
        embed = discord.Embed(
            title="🧠 DeepAI Commands",
            description="Access various DeepAI models with these commands:",
            color=discord.Color.teal()
        )
        
        embed.add_field(
            name="Text Generation",
            value=(
                "`!dai text-generator <prompt>` - Generate text from a prompt\n"
                "`!dai chatbot <message>` - Chat with an AI assistant\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Image Generation & Manipulation",
            value=(
                "`!dai dream <prompt>` - Generate an image from text\n"
                "`!dai colorize <image_url>` - Colorize a black and white image\n"
                "`!dai toonify <image_url>` - Convert a photo to a cartoon\n"
                "`!dai enhance <image_url>` - Enhance image resolution\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Analysis",
            value=(
                "`!dai sentiment <text>` - Analyze text sentiment\n"
                "`!dai summarize <text>` - Summarize long text\n"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use !dai or !deepai as the command prefix")
        
        await ctx.send(embed=embed)

    @deepai_group.command(name="text-generator", aliases=["text"])
    async def text_generator(self, ctx, *, prompt: str):
        """Generate text from a prompt using DeepAI"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("text-generator", text=prompt)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output_text = response.get("output", "No output generated")
            
            # Split into chunks if too long
            if len(output_text) > 1900:
                chunks = [output_text[i:i+1900] for i in range(0, len(output_text), 1900)]
                
                embed = discord.Embed(
                    title="📝 Generated Text",
                    description=f"**Prompt:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
                    color=discord.Color.teal()
                )
                
                await ctx.send(embed=embed)
                
                for i, chunk in enumerate(chunks):
                    await ctx.send(f"```{chunk}```")
            else:
                embed = discord.Embed(
                    title="📝 Generated Text",
                    description=f"**Prompt:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n\n{output_text}",
                    color=discord.Color.teal()
                )
                
                embed.set_footer(text="Powered by DeepAI")
                await ctx.send(embed=embed)
    
    @deepai_group.command(name="chatbot", aliases=["chat"])
    async def chatbot(self, ctx, *, message: str):
        """Chat with the DeepAI chatbot"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("chatbot", text=message)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output_text = response.get("output", "No response generated")
            
            embed = discord.Embed(
                title="💬 DeepAI Chat",
                color=discord.Color.teal()
            )
            
            embed.add_field(name="You", value=message, inline=False)
            embed.add_field(name="DeepAI", value=output_text, inline=False)
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)

    @deepai_group.command(name="dream", aliases=["image"])
    async def dream(self, ctx, *, prompt: str):
        """Generate an image from text using DeepAI"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("text2img", text=prompt)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            image_url = response.get("output_url")
            if not image_url:
                await ctx.send("❌ No image was generated.")
                return
            
            embed = discord.Embed(
                title="🎨 Generated Image",
                description=f"**Prompt:** {prompt}",
                color=discord.Color.teal()
            )
            
            embed.set_image(url=image_url)
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)
    
    @deepai_group.command(name="colorize")
    async def colorize(self, ctx, image_url: str):
        """Colorize a black and white image"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("colorizer", image=image_url)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output_url = response.get("output_url")
            if not output_url:
                await ctx.send("❌ No image was generated.")
                return
            
            embed = discord.Embed(
                title="🎨 Colorized Image",
                color=discord.Color.teal()
            )
            
            embed.set_image(url=output_url)
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)
    
    @deepai_group.command(name="toonify")
    async def toonify(self, ctx, image_url: str):
        """Convert a photo to a cartoon"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("toonify", image=image_url)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output_url = response.get("output_url")
            if not output_url:
                await ctx.send("❌ No image was generated.")
                return
            
            embed = discord.Embed(
                title="🎨 Toonified Image",
                color=discord.Color.teal()
            )
            
            embed.set_image(url=output_url)
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)

    @deepai_group.command(name="enhance")
    async def enhance(self, ctx, image_url: str):
        """Enhance image resolution"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("torch-srgan", image=image_url)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output_url = response.get("output_url")
            if not output_url:
                await ctx.send("❌ No image was generated.")
                return
            
            embed = discord.Embed(
                title="🔍 Enhanced Image",
                color=discord.Color.teal()
            )
            
            embed.set_image(url=output_url)
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)
    
    @deepai_group.command(name="sentiment")
    async def sentiment(self, ctx, *, text: str):
        """Analyze text sentiment"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("sentiment-analysis", text=text)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output = response.get("output", [])
            if not output:
                await ctx.send("❌ No sentiment analysis was generated.")
                return
            
            embed = discord.Embed(
                title="📊 Sentiment Analysis",
                description=f"**Text:** {text[:100]}{'...' if len(text) > 100 else ''}",
                color=discord.Color.teal()
            )
            
            # Format the sentiment output
            sentiment_str = ", ".join(output)
            embed.add_field(name="Sentiment", value=sentiment_str)
            
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)
    
    @deepai_group.command(name="summarize")
    async def summarize(self, ctx, *, text: str):
        """Summarize long text"""
        user_id = ctx.author.id
        
        if not self.api_key:
            await ctx.send("❌ DeepAI API key is not configured. Please set the DEEPAI_API_KEY environment variable.")
            return
        
        if self._check_cooldown(user_id):
            await ctx.send(f"⏳ Please wait {self.cooldown_seconds} seconds between DeepAI requests.")
            return
        
        if len(text) < 100:
            await ctx.send("❌ Text is too short to summarize. Please provide a longer text.")
            return
        
        async with ctx.typing():
            response = await self._call_deepai_api("summarization", text=text)
            
            if "error" in response:
                await ctx.send(f"❌ Error: {response['error']}")
                return
            
            self._update_cooldown(user_id)
            
            output = response.get("output", "No summary was generated.")
            
            embed = discord.Embed(
                title="📜 Text Summary",
                color=discord.Color.teal()
            )
            
            embed.add_field(name="Original Text (excerpt)", value=f"{text[:100]}...", inline=False)
            embed.add_field(name="Summary", value=output, inline=False)
            
            embed.set_footer(text="Powered by DeepAI")
            
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DeepAI(bot))
