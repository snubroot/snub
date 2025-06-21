import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime
import asyncio
from collections import Counter
from openai import OpenAI
import config

class DreamJournal(commands.Cog):
    """Dream journal and lucid dreaming log commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.dreams_path = "data/user_dreams.json"
        self.symbols_path = "data/dream_symbols.json"
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Create directories and files if they don't exist
        os.makedirs(os.path.dirname(self.dreams_path), exist_ok=True)
        
        # Initialize dreams file if it doesn't exist
        if not os.path.exists(self.dreams_path):
            with open(self.dreams_path, "w") as f:
                json.dump({}, f)
                
        # Initialize dream symbols file with default interpretations if it doesn't exist
        if not os.path.exists(self.symbols_path):
            default_symbols = {
                "water": "Emotions, unconscious mind, flow of life",
                "flying": "Freedom, escape, perspective, transcending limitations",
                "falling": "Insecurity, anxiety, loss of control",
                "teeth": "Anxiety, self-image, communication concerns",
                "chase": "Avoidance, running from problems or fears",
                "house": "Self, mind, personal space and boundaries",
                "death": "Transformation, endings, change, rebirth",
                "naked": "Vulnerability, exposure, authenticity, fear of judgment",
                "test": "Self-evaluation, fear of failure, feeling unprepared",
                "money": "Self-worth, value, energy exchange",
                "snake": "Transformation, healing, knowledge, fear, temptation",
                "fire": "Passion, transformation, anger, destruction, purification",
                "baby": "New beginnings, vulnerability, innocence, potential",
                "food": "Knowledge, spiritual nourishment, emotional needs",
                "car": "Direction in life, control, personal journey",
                "door": "Opportunities, transitions, choices",
                "mirror": "Self-reflection, identity, seeing your true self",
                "bridge": "Transition, crossing boundaries, connection",
                "mountain": "Challenge, achievement, perspective",
                "ocean": "Unconscious mind, emotion, vastness, mystery",
                "forest": "Unconscious, unknown aspects of self, exploration",
                "light": "Awareness, insight, guidance, truth",
                "darkness": "Unknown, fear, mystery, unconscious",
                "animals": "Instincts, traits, aspects of self",
                "clock": "Passage of time, pressure, mortality"
            }
            with open(self.symbols_path, "w") as f:
                json.dump(default_symbols, f, indent=4)

    @commands.command(name="dreamlog")
    async def dream_log(self, ctx, *, entry=None):
        """Log a dream entry
        
        Example: !dreamlog I was flying over mountains and saw a river
        """
        if not entry:
            await ctx.send("Please provide a dream description. Example: `!dreamlog I was flying over mountains`")
            return
            
        # Extract potential symbols from the entry
        symbols = self._extract_symbols(entry)
        
        # Save the dream entry
        dream_id = self._save_dream(ctx.author.id, entry, symbols)
        
        # Create an embed response
        embed = discord.Embed(
            title="✨ Dream Logged",
            description=f"Your dream has been recorded with ID: `{dream_id}`",
            color=discord.Color.purple()
        )
        
        if symbols:
            embed.add_field(
                name="Detected Symbols",
                value=", ".join([f"`{symbol}`" for symbol in symbols]),
                inline=False
            )
            embed.add_field(
                name="Get Interpretation",
                value=f"Use `!interpretdream {dream_id}` to get an interpretation of these symbols in your dream",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="dreamstats")
    async def dream_stats(self, ctx):
        """View statistics about your dream journal
        
        Shows frequency of symbols, lucidity rate, and more
        """
        user_id = str(ctx.author.id)
        dreams = self._get_user_dreams(user_id)
        
        if not dreams:
            await ctx.send("You haven't logged any dreams yet. Use `!dreamlog` to start your dream journal!")
            return
            
        # Calculate statistics
        total_dreams = len(dreams)
        
        # Count symbols
        all_symbols = []
        for dream in dreams:
            all_symbols.extend(dream.get("symbols", []))
        
        symbol_counts = Counter(all_symbols)
        top_symbols = symbol_counts.most_common(5)
        
        # Create an embed response
        embed = discord.Embed(
            title="🌙 Dream Journal Statistics",
            description=f"Statistics for {ctx.author.display_name}'s dream journal",
            color=discord.Color.dark_purple()
        )
        
        embed.add_field(
            name="Total Dreams Logged",
            value=str(total_dreams),
            inline=True
        )
        
        embed.add_field(
            name="First Dream Logged",
            value=dreams[0].get("date", "Unknown"),
            inline=True
        )
        
        embed.add_field(
            name="Latest Dream",
            value=dreams[-1].get("date", "Unknown"),
            inline=True
        )
        
        if top_symbols:
            embed.add_field(
                name="Most Common Symbols",
                value="\n".join([f"`{symbol}`: {count} times" for symbol, count in top_symbols]),
                inline=False
            )
        
        embed.set_footer(text="Use !interpretdream <id> to interpret a specific dream")
        await ctx.send(embed=embed)

    @commands.command(name="interpretdream")
    async def interpret_dream(self, ctx, entry_id=None):
        """Get an interpretation of a dream entry
        
        Example: !interpretdream 1234567890
        """
        if not entry_id:
            await ctx.send("Please provide a dream entry ID. Example: `!interpretdream 1234567890`")
            return
            
        user_id = str(ctx.author.id)
        dreams = self._get_user_dreams(user_id)
        
        # Find the dream with the matching ID
        dream = None
        for d in dreams:
            if d.get("id") == entry_id:
                dream = d
                break
                
        if not dream:
            await ctx.send(f"No dream found with ID: `{entry_id}`. Use `!dreamlog` to record a dream first.")
            return
        
        dream_content = dream.get("content", "")
        if not dream_content:
            await ctx.send("This dream entry has no content to interpret.")
            return
        
        # Get the symbols for reference
        symbols = dream.get("symbols", [])
        
        # Load symbol interpretations for reference
        with open(self.symbols_path, "r") as f:
            symbol_meanings = json.load(f)
        
        # Send a typing indicator while processing
        async with ctx.typing():
            try:
                # Get AI interpretation
                interpretation = await self._get_ai_interpretation(dream_content, symbols, symbol_meanings)
                
                # Create an embed response
                embed = discord.Embed(
                    title="🔮 Dream Interpretation",
                    description=f"Interpretation of dream from {dream.get('date')}",
                    color=discord.Color.blue()
                )
                
                # Add the dream content (truncate if needed)
                dream_content_truncated = dream_content[:1000] + "..." if len(dream_content) > 1000 else dream_content
                embed.add_field(
                    name="Dream Content",
                    value=dream_content_truncated,
                    inline=False
                )
                
                # If we have symbols, show them
                if symbols:
                    symbols_text = ", ".join([f"`{symbol}`" for symbol in symbols])
                    symbols_text = symbols_text[:1000] + "..." if len(symbols_text) > 1000 else symbols_text
                    embed.add_field(
                        name="Detected Symbols",
                        value=symbols_text,
                        inline=False
                    )
                
                # Add the AI interpretation (truncate if needed)
                interpretation_truncated = interpretation[:1000] + "..." if len(interpretation) > 1000 else interpretation
                embed.add_field(
                    name="AI Interpretation",
                    value=interpretation_truncated,
                    inline=False
                )
                
                embed.set_footer(text="Dream interpretations are subjective and for entertainment purposes")
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error generating dream interpretation: {str(e)}")

    def _save_dream(self, user_id, content, symbols):
        """Save a user's dream entry"""
        user_id = str(user_id)
        
        # Generate a unique ID for the dream
        dream_id = f"{int(datetime.now().timestamp())}"
        
        # Load existing dreams
        with open(self.dreams_path, "r") as f:
            dreams = json.load(f)
            
        # Initialize user entry if it doesn't exist
        if user_id not in dreams:
            dreams[user_id] = []
            
        # Add new dream entry
        dream_entry = {
            "id": dream_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "content": content,
            "symbols": symbols
        }
        
        dreams[user_id].append(dream_entry)
        
        # Save updated dreams
        with open(self.dreams_path, "w") as f:
            json.dump(dreams, f, indent=4)
            
        return dream_id
        
    def _get_user_dreams(self, user_id):
        """Get all dreams for a user"""
        user_id = str(user_id)
        
        # Load dreams
        with open(self.dreams_path, "r") as f:
            dreams = json.load(f)
            
        # Return user's dreams or empty list if none
        return dreams.get(user_id, [])
        
    def _extract_symbols(self, content):
        """Extract known symbols from dream content"""
        content = content.lower()
        
        # Load known symbols
        with open(self.symbols_path, "r") as f:
            symbols = json.load(f)
            
        # Find symbols in content
        found_symbols = []
        for symbol in symbols.keys():
            if symbol in content:
                found_symbols.append(symbol)
                
        return found_symbols
        
    async def _get_ai_interpretation(self, dream_content, symbols=None, symbol_meanings=None):
        """Get an AI-powered interpretation of the dream content"""
        try:
            # Prepare symbols information if available
            symbols_info = ""
            if symbols and symbol_meanings:
                symbols_info = "\nDetected symbols in the dream:\n"
                for symbol in symbols:
                    meaning = symbol_meanings.get(symbol, "Unknown meaning")
                    symbols_info += f"- {symbol}: {meaning}\n"
            
            # Create the prompt for OpenAI
            prompt = f"""Please interpret the following dream. Provide insights into possible psychological meanings, 
            emotional themes, and potential connections to the dreamer's life. Keep the interpretation very concise (max 150 words).
            
            Dream content: {dream_content}
            {symbols_info}
            """
            
            # Call OpenAI API with more controlled parameters
            response = await self._run_openai_call(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",  # Using 3.5-turbo for faster responses and lower cost
                messages=[
                    {"role": "system", "content": "You are a thoughtful dream interpreter. Provide insightful but concise interpretations that respect the dreamer's experience. Avoid being overly deterministic or making absolute statements about the dreamer's life. Instead, offer possibilities and reflections that might help them understand the dream's significance. Keep your response under 150 words."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7,
                presence_penalty=0.2,
                frequency_penalty=0.5
            )
            
            # Extract and return the interpretation
            interpretation = response.choices[0].message.content.strip()
            return interpretation
            
        except Exception as e:
            # Fallback to basic interpretation if API fails
            return self._generate_basic_interpretation(dream_content, symbols, symbol_meanings)
    
    async def _run_openai_call(self, func, *args, **kwargs):
        """Run an OpenAI API call in a thread to prevent blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: func(*args, **kwargs)
        )
    
    def _generate_basic_interpretation(self, content, symbols, symbol_meanings):
        """Generate a basic interpretation based on the dream content and symbols (fallback method)"""
        if not symbols:
            return "This dream appears to contain personal elements that may reflect your current thoughts, feelings, or experiences. Consider how the events and emotions in the dream might relate to your waking life."
            
        # Start with a general statement
        interpretation = "This dream appears to involve themes of "
        
        # Add themes based on symbols
        themes = []
        for symbol in symbols:
            if symbol in symbol_meanings:
                meaning = symbol_meanings[symbol].split(",")[0].lower()
                themes.append(meaning)
                
        if themes:
            interpretation += ", ".join(themes[:3])
            
            # Add a reflective question
            reflective_questions = [
                "Consider how these symbols might relate to your current life situation.",
                "Reflect on how these symbols might represent aspects of yourself or your emotions.",
                "Think about what changes or insights these dream symbols might be suggesting.",
                "Consider what parts of yourself these symbols might represent.",
                "Reflect on how these dream elements connect to your waking life."
            ]
            
            interpretation += ". " + random.choice(reflective_questions)
        else:
            interpretation = "The elements in this dream suggest personal themes that may be unique to you. Consider keeping a dream journal to track patterns over time."
            
        return interpretation

async def setup(bot):
    await bot.add_cog(DreamJournal(bot))
