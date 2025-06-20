import discord
from discord.ext import commands
import random
import json
import os
import asyncio
from openai import OpenAI
import config
from collections import deque

class WouldURatherCog(commands.Cog):
    """Fun game module that generates 'Would You Rather' questions. Uses OpenAI to create unique and engaging hypothetical scenarios where users must choose between two options. Features include interactive buttons for voting, percentage displays for choices, and a system to avoid question repetition."""
    def __init__(self, bot):
        self.bot = bot
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.recent_questions = deque(maxlen=50)
        self.questions_file = "data/wouldurather_questions.json"
        self.load_questions()
        
    def get_random_string(self, length):
        random_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(random_chars) for _ in range(length))
    
    def load_questions(self):
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(self.questions_file):
                with open(self.questions_file, 'r') as f:
                    saved_questions = json.load(f)
                    self.recent_questions = deque(saved_questions, maxlen=50)
        except Exception:
            self.recent_questions = deque(maxlen=50)
    
    def save_questions(self):
        try:
            with open(self.questions_file, 'w') as f:
                json.dump(list(self.recent_questions), f)
        except Exception:
            pass
    
    async def generate_question(self):
        try:
            response = await self.run_openai_call(
                self.openai_client.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a creative assistant that generates 'Would You Rather' questions. Generate a single would you rather question with two options. Return ONLY a JSON object with the format {\"option_a\": \"first option\", \"option_b\": \"second option\"}. Do not include any other text or explanation."}
                ],
                temperature=0.9
            )
            
            content = response.choices[0].message.content
            question_data = json.loads(content)
            
            option_a = question_data["option_a"]
            option_b = question_data["option_b"]
            
            question_pair = (option_a, option_b)
            
            if question_pair in self.recent_questions:
                return await self.generate_question()
            
            self.recent_questions.append(question_pair)
            self.save_questions()
            
            return option_a, option_b
            
        except Exception as e:
            raise Exception(f"Failed to generate question: {str(e)}")
    
    async def run_openai_call(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: func(*args, **kwargs)
        )
    
    @commands.command(name="wouldurather")
    async def wouldurather(self, ctx):
        loading_embed = discord.Embed(
            title="🔄 Generating a would you rather question...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=loading_embed)
        
        id1 = f"{self.get_random_string(20)}-{self.get_random_string(20)}"
        id2 = f"{self.get_random_string(20)}-{self.get_random_string(20)}"
        
        try:
            option_a, option_b = await self.generate_question()
            
            votes_a = random.randint(30, 70)
            votes_b = 100 - votes_a
            
            percentage_a = f"{votes_a}%"
            percentage_b = f"{votes_b}%"
            
            button_a = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Option A",
                custom_id=id1
            )
            
            button_b = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Option B",
                custom_id=id2
            )
            
            view = discord.ui.View()
            view.add_item(button_a)
            view.add_item(button_b)
            
            embed = discord.Embed(
                title="🤔 Would you rather...",
                description=f"**A)** {option_a}\n**B)** {option_b}",
                color=discord.Color.blue()
            )
            
            await message.edit(embed=embed, view=view)
            
            async def button_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("This isn't your game!", ephemeral=True)
                    return
                
                choice = interaction.data["custom_id"]
                
                if choice == id1:
                    button_a.style = discord.ButtonStyle.primary
                    button_a.label = f"Option A ({percentage_a})"
                    button_a.disabled = True
                    
                    button_b.style = discord.ButtonStyle.secondary
                    button_b.label = f"Option B ({percentage_b})"
                    button_b.disabled = True
                    
                    result_embed = discord.Embed(
                        title="🤔 Would you rather...",
                        description=f"**A) {option_a} ({percentage_a})**\nB) {option_b} ({percentage_b})",
                        color=discord.Color.blue()
                    )
                    
                elif choice == id2:
                    button_a.style = discord.ButtonStyle.secondary
                    button_a.label = f"Option A ({percentage_a})"
                    button_a.disabled = True
                    
                    button_b.style = discord.ButtonStyle.primary
                    button_b.label = f"Option B ({percentage_b})"
                    button_b.disabled = True
                    
                    result_embed = discord.Embed(
                        title="🤔 Would you rather...",
                        description=f"A) {option_a} ({percentage_a})\n**B) {option_b} ({percentage_b})**",
                        color=discord.Color.blue()
                    )
                
                await interaction.response.edit_message(embed=result_embed, view=view)
                view.stop()
            
            button_a.callback = button_callback
            button_b.callback = button_callback
            
            await view.wait()
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while generating would you rather questions: {str(e)}",
                color=discord.Color.red()
            )
            await message.edit(embed=error_embed, view=None)

async def setup(bot):
    await bot.add_cog(WouldURatherCog(bot))
