import os
import io
import discord
import logging
import asyncio
import json
from discord.ext import commands
from openai import OpenAI
from datetime import datetime
import config

class OpenAICog(commands.Cog):
    """OpenAI integration for text and image generation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # User cooldowns - track timestamps of last usage
        self.cooldowns = {}
        
        # Daily usage tracking
        self.daily_usage = {}
        
        # Conversation memory storage
        self.memory_file = "data/conversation_memory.json"
        self.memory = self._load_memory()
        
        # Default settings
        self.default_model = "gpt-4o"
        self.cooldown_seconds = 10
        self.max_daily_uses = 25
        self.max_tokens = 1000
        self.max_memory_messages = 10  # Maximum number of message pairs before summarization
        self.token_threshold = 2000    # Approximate token threshold for summarization
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        logging.info("OpenAI cog initialized")
    
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
    
    def _load_memory(self):
        """Load conversation memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading conversation memory: {str(e)}")
            return {}
    
    def _save_memory(self):
        """Save conversation memory to file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f)
        except Exception as e:
            logging.error(f"Error saving conversation memory: {str(e)}")
    
    def _get_memory(self, user_id):
        """Get memory for a specific user"""
        user_id = str(user_id)  # Convert to string for JSON compatibility
        if user_id not in self.memory:
            self.memory[user_id] = {
                "messages": [],
                "summary": ""
            }
        return self.memory[user_id]
    
    def _clear_memory(self, user_id):
        """Clear memory for a specific user"""
        user_id = str(user_id)  # Convert to string for JSON compatibility
        if user_id in self.memory:
            self.memory[user_id] = {
                "messages": [],
                "summary": ""
            }
            self._save_memory()
    
    async def _summarize_conversation(self, user_id):
        """Summarize the conversation to reduce token usage"""
        user_memory = self._get_memory(user_id)
        messages = user_memory["messages"]
        summary = user_memory["summary"]
        
        # If we have a summary and messages, create a prompt for summarization
        if messages:
            system_prompt = "Summarize the following conversation concisely while preserving key information, context, and user preferences. This summary will be used as context for future conversation."
            
            # Create the conversation history to summarize
            conversation_to_summarize = []
            
            # Add previous summary if it exists
            if summary:
                conversation_to_summarize.append({"role": "system", "content": f"Previous conversation summary: {summary}"})
            
            # Add messages to summarize
            conversation_to_summarize.extend(messages)
            
            # Add summarization instruction
            conversation_to_summarize.append({"role": "user", "content": "Please create a concise summary of our conversation so far. Include important details, preferences, and context."})
            
            try:
                # Call OpenAI API for summarization
                response = await self._run_openai_call(
                    self.openai_client.chat.completions.create,
                    model=self.default_model,
                    messages=[{"role": "system", "content": system_prompt}] + conversation_to_summarize,
                    max_tokens=500
                )
                
                # Extract the summary
                new_summary = response.choices[0].message.content
                
                # Update memory with the new summary and clear messages
                user_memory["summary"] = new_summary
                user_memory["messages"] = []
                self._save_memory()
                
                return new_summary
            except Exception as e:
                logging.error(f"Error in conversation summarization: {str(e)}")
                return summary  # Return the old summary if there's an error
        
        return summary
    
    def _estimate_tokens(self, text):
        """Estimate the number of tokens in a text"""
        # A very rough estimation: ~4 characters per token for English text
        return len(text) // 4
    
    def _estimate_messages_tokens(self, messages):
        """Estimate the total tokens in a list of messages"""
        total = 0
        for message in messages:
            total += self._estimate_tokens(message["content"])
        return total
    
    @commands.command(name="ask", aliases=["ai", "gpt"])
    async def ask(self, ctx, *, prompt: str):
        """Ask a question to OpenAI's GPT model
        
        Usage: !ask <your question>
        Example: !ask What is the capital of France?
        """
        user_id = ctx.author.id
        
        # Check if this is a command to clear memory
        if prompt.lower().strip() in ["clear memory", "forget", "reset", "clear"]:
            self._clear_memory(user_id)
            embed = discord.Embed(
                title="🧹 Memory Cleared",
                description="I've cleared my memory of our previous conversations.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return
        
        # Check cooldown
        if self._check_cooldown(user_id):
            cooldown_remaining = self.cooldown_seconds - (datetime.now() - self.cooldowns[user_id]).total_seconds()
            embed = discord.Embed(
                title="⏳ Cooldown",
                description=f"Please wait {int(cooldown_remaining)} more seconds before using this command again.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Check daily limit
        if self._check_daily_limit(user_id):
            embed = discord.Embed(
                title="❌ Daily Limit Reached",
                description=f"You've reached your daily limit of {self.max_daily_uses} AI requests.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Send typing indicator to show the bot is processing
        async with ctx.typing():
            try:
                # Get user memory
                user_memory = self._get_memory(user_id)
                messages = user_memory["messages"]
                summary = user_memory["summary"]
                
                # Check if we need to summarize (too many messages or token threshold exceeded)
                if len(messages) >= self.max_memory_messages or self._estimate_messages_tokens(messages) > self.token_threshold:
                    summary = await self._summarize_conversation(user_id)
                    messages = []  # Reset messages after summarization
                
                # Build the messages array for the API call
                api_messages = []
                
                # System message with instructions
                system_content = "You are a helpful assistant that provides concise and accurate information."
                if summary:
                    system_content += f" Here's a summary of the previous conversation: {summary}"
                
                api_messages.append({"role": "system", "content": system_content})
                
                # Add conversation history
                api_messages.extend(messages)
                
                # Add current user message
                api_messages.append({"role": "user", "content": prompt})
                
                # Call OpenAI API
                response = await self._run_openai_call(
                    self.openai_client.chat.completions.create,
                    model=self.default_model,
                    messages=api_messages,
                    max_tokens=self.max_tokens
                )
                
                # Update cooldown and usage
                self._update_cooldown(user_id)
                self._increment_daily_usage(user_id)
                
                # Extract the response text
                response_text = response.choices[0].message.content
                
                # Update memory with the new messages
                messages.append({"role": "user", "content": prompt})
                messages.append({"role": "assistant", "content": response_text})
                user_memory["messages"] = messages
                self._save_memory()
                
                # Create embed response
                embed = discord.Embed(
                    title="🤖 AI Response",
                    description=response_text,
                    color=discord.Color.blue()
                )
                
                # Add memory indicator to footer
                memory_status = "Using conversation summary" if summary else f"Conversation memory: {len(messages)//2} exchanges"
                embed.set_footer(text=f"{memory_status} | Requested by {ctx.author.name} | Model: {self.default_model}")
                embed.timestamp = datetime.now()
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logging.error(f"Error in OpenAI API call: {str(e)}")
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred while processing your request: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
    
    @commands.command(name="imagine", aliases=["img", "image"])
    async def imagine(self, ctx, *, prompt: str):
        """Generate an image using DALL-E
        
        Usage: !imagine <image description>
        Example: !imagine A cat wearing a space suit on the moon
        """
        user_id = ctx.author.id
        
        # Check cooldown
        if self._check_cooldown(user_id):
            cooldown_remaining = self.cooldown_seconds - (datetime.now() - self.cooldowns[user_id]).total_seconds()
            embed = discord.Embed(
                title="⏳ Cooldown",
                description=f"Please wait {int(cooldown_remaining)} more seconds before using this command again.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Check daily limit
        if self._check_daily_limit(user_id):
            embed = discord.Embed(
                title="❌ Daily Limit Reached",
                description=f"You've reached your daily limit of {self.max_daily_uses} AI requests.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Send typing indicator to show the bot is processing
        async with ctx.typing():
            try:
                # Call OpenAI API for image generation
                response = await self._run_openai_call(
                    self.openai_client.images.generate,
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024"
                )
                
                # Update cooldown and usage
                self._update_cooldown(user_id)
                self._increment_daily_usage(user_id)
                
                # Get the image URL
                image_url = response.data[0].url
                
                # Create embed response
                embed = discord.Embed(
                    title="🎨 Generated Image",
                    description=f"**Prompt:** {prompt}",
                    color=discord.Color.purple()
                )
                
                embed.set_image(url=image_url)
                embed.set_footer(text=f"Generated for {ctx.author.name} | Model: DALL-E")
                embed.timestamp = datetime.now()
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logging.error(f"Error in OpenAI image generation: {str(e)}")
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred while generating your image: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
    
    @commands.command(name="ai-info")
    async def ai_info(self, ctx):
        """Get information about the OpenAI integration"""
        user_id = ctx.author.id
        
        # Calculate remaining uses
        remaining_uses = self.max_daily_uses
        if user_id in self.daily_usage:
            remaining_uses = max(0, self.max_daily_uses - self.daily_usage[user_id])
        
        # Get memory status
        user_memory = self._get_memory(user_id)
        has_summary = bool(user_memory["summary"])
        message_count = len(user_memory["messages"]) // 2
        
        memory_status = "Using conversation summary" if has_summary else f"{message_count} conversation exchanges stored"
        
        embed = discord.Embed(
            title="🤖 OpenAI Integration",
            description="Information about the AI features",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Text Model",
            value=self.default_model,
            inline=True
        )
        
        embed.add_field(
            name="Image Model",
            value="DALL-E 3",
            inline=True
        )
        
        embed.add_field(
            name="Cooldown",
            value=f"{self.cooldown_seconds} seconds",
            inline=True
        )
        
        embed.add_field(
            name="Daily Limit",
            value=f"{self.max_daily_uses} requests per user",
            inline=True
        )
        
        embed.add_field(
            name="Your Remaining Uses",
            value=f"{remaining_uses} requests",
            inline=True
        )
        
        embed.add_field(
            name="Memory Status",
            value=memory_status,
            inline=True
        )
        
        embed.add_field(
            name="Commands",
            value="• `!ask <question>` - Ask the AI a question\n• `!ask clear` - Clear conversation memory\n• `!imagine <prompt>` - Generate an image",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OpenAICog(bot))
