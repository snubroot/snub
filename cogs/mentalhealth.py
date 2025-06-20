import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta
import asyncio
import csv
import io

class MentalHealth(commands.Cog):
    """Mental health check-in and mood tracking commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.moods_path = "data/user_moods.json"
        self.prompts_path = "data/mental_prompts.json"
        self.reminders_path = "data/mental_reminders.json"
        
        # Create directories and files if they don't exist
        os.makedirs(os.path.dirname(self.moods_path), exist_ok=True)
        
        # Initialize moods file if it doesn't exist
        if not os.path.exists(self.moods_path):
            with open(self.moods_path, "w") as f:
                json.dump({}, f)
                
        # Initialize reminders file if it doesn't exist
        if not os.path.exists(self.reminders_path):
            with open(self.reminders_path, "w") as f:
                json.dump({}, f)
                
        # Start the reminder check background task
        self.reminder_task = self.bot.loop.create_task(self.check_reminders())
        
        # Initialize prompts file with default prompts if it doesn't exist
        if not os.path.exists(self.prompts_path):
            default_prompts = {
                "general": [
                    "What's one small thing you're grateful for today?",
                    "What's something that made you smile recently?",
                    "What's one thing you're looking forward to?",
                    "What's a small victory you've had recently?",
                    "What's something you're proud of yourself for?",
                    "What's one thing you can do today to take care of yourself?",
                    "What's a moment of peace you experienced recently?",
                    "What's a quality you appreciate about yourself?",
                    "What's a simple pleasure that brings you joy?",
                    "What's something you've learned about yourself recently?",
                    "What would make today feel like a good day for you?",
                    "What's something you can let go of today?"
                ],
                "anxiety": [
                    "What's one thing you can control right now?",
                    "What are three things you can see, hear, and feel right now?",
                    "What's a thought that's causing you anxiety? Is there evidence for or against it?",
                    "What's a calming activity you could do for 5 minutes?",
                    "What would you tell a friend who was feeling this way?",
                    "What's the worst that could happen? How would you cope with it?",
                    "What's a more balanced way to look at this situation?",
                    "When have you successfully handled something like this before?",
                    "What's one small action that would help you feel more secure?",
                    "What's a mantra or phrase that helps you feel calm?",
                    "How can you ground yourself in the present moment?",
                    "What are your anxiety triggers and how can you prepare for them?"
                ],
                "depression": [
                    "What's one tiny thing that brought you joy recently?",
                    "What's something you've accomplished that you're proud of?",
                    "What's one small step you could take today?",
                    "What's a kind message you could tell yourself right now?",
                    "What's something you're looking forward to, no matter how small?",
                    "What's a small way you could connect with someone today?",
                    "What's an activity that used to bring you joy that you could try again?",
                    "What's a negative thought you can challenge today?",
                    "What's one healthy habit you could maintain or start?",
                    "What's something that gives you a sense of purpose?",
                    "What's a way you could be gentle with yourself today?",
                    "What's a memory that brings you comfort or happiness?"
                ],
                "stress": [
                    "What's one thing you could take off your plate right now?",
                    "What's a boundary you could set to protect your energy?",
                    "What's a simple self-care activity you could do today?",
                    "What would help you feel more grounded right now?",
                    "What's something that's worked for you in the past when you felt stressed?",
                    "What's a task you could delegate or postpone?",
                    "What's a physical tension you're holding that you could release?",
                    "What's a realistic expectation for yourself today?",
                    "What's a way to break down a stressful task into smaller steps?",
                    "What's a stress trigger you could minimize or avoid?",
                    "What's a breathing technique that helps you relax?",
                    "How could you create a moment of calm in your day?"
                ],
                "motivation": [
                    "What's one small step you could take toward your goal?",
                    "What's a way to make your current task more meaningful?",
                    "What would make this task more enjoyable?",
                    "What's the purpose behind what you're trying to do?",
                    "How would your future self thank you for taking action today?",
                    "What's a way to reward yourself after completing a task?",
                    "What's the smallest possible action you could take right now?",
                    "What's a positive outcome you're working toward?",
                    "What's an obstacle in your way and how might you overcome it?",
                    "What's a strength you have that could help with your current challenge?",
                    "What would happen if you took action despite not feeling motivated?",
                    "Who could support or inspire you right now?"
                ]
            }
            
            with open(self.prompts_path, "w") as f:
                json.dump(default_prompts, f, indent=4)
    
    @commands.command(name="checkin")
    async def check_in(self, ctx):
        """Start a mental health check-in conversation
        
        This begins a private conversation about your current mood
        """
        # Create a welcoming embed
        embed = discord.Embed(
            title="🧘 Mental Health Check-In",
            description="How are you feeling today, really?\n\nReply with `good`, `okay`, `bad`, or use `!mood` followed by a word that describes your current state.",
            color=discord.Color.teal()
        )
        
        embed.add_field(
            name="What's Next?",
            value="After sharing your mood, you can:\n• Type `!prompt` for a general reflection prompt\n• Type `!prompt anxiety` (or depression/stress/motivation) for specific guidance",
            inline=False
        )
        
        embed.set_footer(text="Your responses are private and only stored anonymously for your own tracking")
        
        # Try to DM the user
        try:
            await ctx.author.send(embed=embed)
            if ctx.guild:  # If command was used in a server
                await ctx.send(f"✅ {ctx.author.mention}, I've sent you a private message to check in!")
        except discord.Forbidden:
            await ctx.send(f"❌ {ctx.author.mention}, I couldn't send you a DM. Please enable direct messages from server members and try again.")
    
    @commands.command(name="mood")
    async def record_mood(self, ctx, *, mood_description: str = None):
        """Record your current mood
        
        Example: !mood feeling better today
        """
        if not mood_description:
            await ctx.send("Please describe your mood. For example: `!mood feeling good today`")
            return
        
        # Analyze the mood (simple keyword-based approach)
        mood_keywords = {
            "positive": ["good", "great", "happy", "excited", "joy", "wonderful", "fantastic", "excellent", "amazing", "better"],
            "neutral": ["okay", "fine", "alright", "neutral", "meh", "average"],
            "negative": ["bad", "sad", "depressed", "anxious", "worried", "stressed", "upset", "down", "terrible", "awful"]
        }
        
        # Determine mood category
        mood_category = "neutral"  # Default
        mood_description_lower = mood_description.lower()
        
        for category, keywords in mood_keywords.items():
            if any(keyword in mood_description_lower for keyword in keywords):
                mood_category = category
                break
        
        # Save the mood entry
        await self._save_mood(ctx.author.id, mood_description, mood_category)
        
        # Create response embed
        mood_colors = {
            "positive": discord.Color.green(),
            "neutral": discord.Color.gold(),
            "negative": discord.Color.red()
        }
        
        mood_icons = {
            "positive": "😊",
            "neutral": "😐",
            "negative": "😔"
        }
        
        embed = discord.Embed(
            title=f"{mood_icons[mood_category]} Mood Recorded",
            description=f"I've recorded that you're feeling: **{mood_description}**",
            color=mood_colors[mood_category]
        )
        
        # Suggest next steps based on mood
        if mood_category == "negative":
            embed.add_field(
                name="Would you like a prompt?",
                value="It sounds like you might be having a tough time. Try `!prompt anxiety` or `!prompt depression` for some supportive reflection questions.",
                inline=False
            )
        elif mood_category == "neutral":
            embed.add_field(
                name="Would you like a prompt?",
                value="Try `!prompt motivation` or `!prompt general` for some reflection questions that might help improve your day.",
                inline=False
            )
        else:  # positive
            embed.add_field(
                name="Would you like a prompt?",
                value="That's great to hear! Try `!prompt gratitude` to reflect on what's going well.",
                inline=False
            )
        
        # Add mood tracking info
        embed.add_field(
            name="Mood Tracking",
            value="Use `!moodhistory` to see your mood patterns over time.",
            inline=False
        )
        
        # Try to send as DM if not already in DM
        if ctx.guild:
            try:
                await ctx.author.send(embed=embed)
                await ctx.send(f"✅ {ctx.author.mention}, I've recorded your mood and sent details in a private message!")
            except discord.Forbidden:
                await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    @commands.command(name="prompt")
    async def get_prompt(self, ctx, prompt_type: str = "general"):
        """Get a journaling or reflection prompt
        
        Examples:
        !prompt
        !prompt anxiety
        !prompt depression
        !prompt stress
        !prompt motivation
        """
        # Load prompts
        prompts = self._load_prompts()
        
        # Normalize prompt type
        prompt_type = prompt_type.lower()
        
        # Default to general if prompt type not found
        if prompt_type not in prompts:
            prompt_type = "general"
        
        # Get a random prompt of the specified type
        prompt = random.choice(prompts[prompt_type])
        
        # Create embed
        embed = discord.Embed(
            title=f"🧘 {prompt_type.title()} Reflection",
            description=prompt,
            color=discord.Color.teal()
        )
        
        embed.add_field(
            name="Journaling Tip",
            value="Take a few minutes to reflect on this prompt. Writing down your thoughts, even briefly, can help process emotions.",
            inline=False
        )
        
        embed.set_footer(text="Use !prompt [type] for more prompts • Types: general, anxiety, depression, stress, motivation")
        
        # Send the prompt
        await ctx.send(embed=embed)
    
    @commands.command(name="moodhistory")
    async def mood_history(self, ctx, days: int = 7):
        """View your mood history for the past few days
        
        Example: !moodhistory 14 (for past 14 days)
        """
        # Limit days to reasonable range
        days = max(1, min(days, 30))
        
        # Get user's mood history
        moods = self._get_user_moods(ctx.author.id, days)
        
        if not moods:
            await ctx.send("You don't have any recorded moods yet. Use `!mood` to start tracking!")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"🧠 Your Mood History (Past {days} Days)",
            color=discord.Color.teal()
        )
        
        # Add mood entries (limit to 10 most recent)
        recent_moods = moods[-10:] if len(moods) > 10 else moods
        
        mood_icons = {
            "positive": "😊",
            "neutral": "😐",
            "negative": "😔"
        }
        
        for mood in recent_moods:
            date_str = datetime.fromisoformat(mood["timestamp"]).strftime("%Y-%m-%d %H:%M")
            embed.add_field(
                name=f"{mood_icons[mood['category']]} {date_str}",
                value=mood["description"],
                inline=False
            )
        
        # Add summary
        positive_count = sum(1 for mood in moods if mood["category"] == "positive")
        neutral_count = sum(1 for mood in moods if mood["category"] == "neutral")
        negative_count = sum(1 for mood in moods if mood["category"] == "negative")
        
        embed.add_field(
            name="Summary",
            value=f"😊 Positive: {positive_count}\n😐 Neutral: {neutral_count}\n😔 Challenging: {negative_count}",
            inline=False
        )
        
        # Try to send as DM for privacy
        try:
            await ctx.author.send(embed=embed)
            if ctx.guild:  # If command was used in a server
                await ctx.send(f"✅ {ctx.author.mention}, I've sent your mood history in a private message!")
        except discord.Forbidden:
            # If we can't DM, check if we're already in a DM channel
            if ctx.guild:
                await ctx.send(f"❌ {ctx.author.mention}, I couldn't send you a DM. Please enable direct messages from server members for privacy.")
            else:
                await ctx.send(embed=embed)
    
    @commands.command(name="addprompt")
    @commands.has_permissions(administrator=True)
    async def add_prompt(self, ctx, prompt_type: str, *, prompt_text: str):
        """Add a new prompt to the collection (Admin only)
        
        Example: !addprompt anxiety What's one small step you could take right now?
        """
        # Load existing prompts
        prompts = self._load_prompts()
        
        # Normalize prompt type
        prompt_type = prompt_type.lower()
        
        # Add prompt type if it doesn't exist
        if prompt_type not in prompts:
            prompts[prompt_type] = []
        
        # Add the new prompt
        prompts[prompt_type].append(prompt_text)
        
        # Save prompts
        with open(self.prompts_path, "w") as f:
            json.dump(prompts, f, indent=4)
        
        await ctx.send(f"✅ Added new {prompt_type} prompt: \"{prompt_text}\"")
    
    async def _save_mood(self, user_id, description, category):
        """Save a user's mood entry"""
        # Load current moods
        moods = {}
        if os.path.exists(self.moods_path):
            with open(self.moods_path, "r") as f:
                moods = json.load(f)
        
        # Convert user_id to string for JSON
        user_id = str(user_id)
        
        # Initialize user entry if it doesn't exist
        if user_id not in moods:
            moods[user_id] = []
        
        # Add new mood entry
        moods[user_id].append({
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "category": category
        })
        
        # Save moods
        with open(self.moods_path, "w") as f:
            json.dump(moods, f, indent=4)
    
    def _get_user_moods(self, user_id, days=7):
        """Get a user's mood history for the past n days"""
        # Load moods
        if not os.path.exists(self.moods_path):
            return []
        
        with open(self.moods_path, "r") as f:
            moods = json.load(f)
        
        # Convert user_id to string for JSON
        user_id = str(user_id)
        
        if user_id not in moods:
            return []
        
        # Filter by date (past n days)
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        recent_moods = [
            mood for mood in moods[user_id]
            if datetime.fromisoformat(mood["timestamp"]).timestamp() > cutoff_date
        ]
        
        return recent_moods
    
    @commands.command(name="mental_help")
    async def mental_help(self, ctx):
        """Show help for mental health commands"""
        embed = discord.Embed(
            title="🧠 Mental Health Command Help",
            description="Track your mood and get reflection prompts with these commands:",
            color=discord.Color.teal()
        )
        
        embed.add_field(
            name="Basic Commands",
            value=(
                "`!checkin` - Start a mental health check-in conversation\n"
                "`!mood feeling good today` - Record your current mood\n"
                "`!prompt` - Get a general reflection prompt\n"
                "`!moodhistory` - See your mood patterns over time\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Prompt Categories",
            value="general, anxiety, depression, stress, motivation",
            inline=False
        )
        
        embed.add_field(
            name="Examples",
            value=(
                "`!prompt anxiety` - Get a prompt for anxiety\n"
                "`!prompt motivation` - Get a motivational prompt\n"
                "`!moodhistory 14` - See your moods for the past 14 days\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Privacy Note",
            value="Your mood data is private and only visible to you. Commands work best in DMs for privacy.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    def _load_prompts(self):
        """Load prompts from file"""
        if not os.path.exists(self.prompts_path):
            return {"general": ["How are you feeling today?"]}
        
        with open(self.prompts_path, "r") as f:
            return json.load(f)

    @commands.command(name="remindmecheckin")
    async def remind_me_checkin(self, ctx, frequency="daily", time="20:00"):
        """Set a reminder to do a mental health check-in
        
        Examples:
        !remindmecheckin daily 20:00
        !remindmecheckin weekly 18:30
        """
        # Validate frequency
        if frequency.lower() not in ["daily", "weekly"]:
            await ctx.send("❌ Frequency must be either 'daily' or 'weekly'.")
            return
        
        # Validate time format
        try:
            hour, minute = map(int, time.split(':'))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
        except ValueError:
            await ctx.send("❌ Time must be in 24-hour format (HH:MM).")
            return
        
        # Load current reminders
        reminders = {}
        if os.path.exists(self.reminders_path):
            with open(self.reminders_path, "r") as f:
                reminders = json.load(f)
        
        # Add or update reminder for user
        user_id = str(ctx.author.id)
        reminders[user_id] = {
            "frequency": frequency.lower(),
            "time": time,
            "last_reminded": None,
            "channel_id": ctx.channel.id
        }
        
        # Save reminders
        with open(self.reminders_path, "w") as f:
            json.dump(reminders, f, indent=4)
        
        await ctx.send(f"✅ I'll remind you to do a mental health check-in {frequency} at {time}.")
    
    @commands.command(name="stopcheckinreminder")
    async def stop_checkin_reminder(self, ctx):
        """Stop your mental health check-in reminders"""
        # Load current reminders
        if not os.path.exists(self.reminders_path):
            await ctx.send("❌ You don't have any active reminders.")
            return
        
        with open(self.reminders_path, "r") as f:
            reminders = json.load(f)
        
        user_id = str(ctx.author.id)
        if user_id in reminders:
            del reminders[user_id]
            
            # Save updated reminders
            with open(self.reminders_path, "w") as f:
                json.dump(reminders, f, indent=4)
            
            await ctx.send("✅ Your check-in reminders have been stopped.")
        else:
            await ctx.send("❌ You don't have any active reminders.")
            
    @commands.command(name="exportmoods")
    async def export_moods(self, ctx, format="csv"):
        """Get a DM of your mood log as a file
        
        Examples:
        !exportmoods csv
        !exportmoods json
        """
        user_id = str(ctx.author.id)
        moods = self._get_user_moods(user_id, days=365)  # Get up to a year of moods
        
        if not moods:
            await ctx.send("❌ You don't have any mood entries to export.")
            return
        
        # Confirm in the channel that we're processing
        if ctx.guild:
            await ctx.send(f"✅ {ctx.author.mention}, I'm preparing your mood export. Check your DMs shortly!")
        
        try:
            if format.lower() == "csv":
                # Create CSV in memory
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(["Date", "Time", "Mood Description", "Category"])
                
                # Write data
                for mood in moods:
                    timestamp = datetime.fromisoformat(mood["timestamp"])
                    date = timestamp.strftime("%Y-%m-%d")
                    time = timestamp.strftime("%H:%M:%S")
                    writer.writerow([date, time, mood["description"], mood["category"]])
                
                # Reset cursor and create discord file
                output.seek(0)
                file = discord.File(fp=output, filename=f"mood_log_{ctx.author.name}.csv")
                
                # Send file
                await ctx.author.send("📃 Here's your mood log export:", file=file)
                
            elif format.lower() == "json":
                # Create JSON file
                formatted_moods = []
                for mood in moods:
                    timestamp = datetime.fromisoformat(mood["timestamp"])
                    formatted_moods.append({
                        "date": timestamp.strftime("%Y-%m-%d"),
                        "time": timestamp.strftime("%H:%M:%S"),
                        "description": mood["description"],
                        "category": mood["category"]
                    })
                
                # Convert to JSON string
                json_data = json.dumps(formatted_moods, indent=2)
                
                # Create file in memory
                buffer = io.BytesIO(json_data.encode())
                file = discord.File(fp=buffer, filename=f"mood_log_{ctx.author.name}.json")
                
                # Send file
                await ctx.author.send("📃 Here's your mood log export:", file=file)
                
            else:
                await ctx.author.send(f"❌ Invalid format '{format}'. Please use 'csv' or 'json'.")
                
        except discord.Forbidden:
            if ctx.guild:
                await ctx.send(f"❌ {ctx.author.mention}, I couldn't send you a DM. Please enable direct messages from server members.")
            else:
                await ctx.send("❌ I couldn't create your export file. Please try again later.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while exporting your moods: {str(e)}")
            print(f"Error exporting moods for {ctx.author.id}: {e}")
            
    @commands.command(name="comparemood")
    async def compare_mood(self, ctx, user: discord.Member = None):
        """Compare your mood history with another user
        
        Example: !comparemood @friend
        """
        if not user:
            await ctx.send("❌ Please mention a user to compare moods with.")
            return
            
        if user.id == ctx.author.id:
            await ctx.send("❌ You can't compare moods with yourself.")
            return
            
        # Get both users' mood data
        author_moods = self._get_user_moods(ctx.author.id, days=30)  # Last 30 days
        target_moods = self._get_user_moods(user.id, days=30)
        
        if not author_moods:
            await ctx.send(f"❌ You don't have any mood entries from the last 30 days.")
            return
            
        if not target_moods:
            await ctx.send(f"❌ {user.display_name} doesn't have any mood entries from the last 30 days.")
            return
            
        # Calculate mood statistics
        author_stats = {
            "positive": sum(1 for m in author_moods if m["category"] == "positive"),
            "neutral": sum(1 for m in author_moods if m["category"] == "neutral"),
            "negative": sum(1 for m in author_moods if m["category"] == "negative")
        }
        
        target_stats = {
            "positive": sum(1 for m in target_moods if m["category"] == "positive"),
            "neutral": sum(1 for m in target_moods if m["category"] == "neutral"),
            "negative": sum(1 for m in target_moods if m["category"] == "negative")
        }
        
        # Calculate total entries
        author_total = sum(author_stats.values())
        target_total = sum(target_stats.values())
        
        # Calculate percentages
        author_percentages = {
            "positive": round(author_stats["positive"] / author_total * 100) if author_total else 0,
            "neutral": round(author_stats["neutral"] / author_total * 100) if author_total else 0,
            "negative": round(author_stats["negative"] / author_total * 100) if author_total else 0
        }
        
        target_percentages = {
            "positive": round(target_stats["positive"] / target_total * 100) if target_total else 0,
            "neutral": round(target_stats["neutral"] / target_total * 100) if target_total else 0,
            "negative": round(target_stats["negative"] / target_total * 100) if target_total else 0
        }
        
        # Calculate similarity score (higher is more similar)
        similarity = 100 - (
            abs(author_percentages["positive"] - target_percentages["positive"]) +
            abs(author_percentages["neutral"] - target_percentages["neutral"]) +
            abs(author_percentages["negative"] - target_percentages["negative"])
        ) / 3
        
        # Create embed
        embed = discord.Embed(
            title=f"🔎 Mood Comparison",
            description=f"Comparing the last 30 days of mood entries between {ctx.author.display_name} and {user.display_name}",
            color=discord.Color.purple()
        )
        
        # Add author stats
        embed.add_field(
            name=f"{ctx.author.display_name}'s Moods",
            value=(
                f"😊 Positive: {author_stats['positive']} ({author_percentages['positive']}%)\n"
                f"😐 Neutral: {author_stats['neutral']} ({author_percentages['neutral']}%)\n"
                f"😔 Challenging: {author_stats['negative']} ({author_percentages['negative']}%)\n"
                f"Total entries: {author_total}"
            ),
            inline=True
        )
        
        # Add target user stats
        embed.add_field(
            name=f"{user.display_name}'s Moods",
            value=(
                f"😊 Positive: {target_stats['positive']} ({target_percentages['positive']}%)\n"
                f"😐 Neutral: {target_stats['neutral']} ({target_percentages['neutral']}%)\n"
                f"😔 Challenging: {target_stats['negative']} ({target_percentages['negative']}%)\n"
                f"Total entries: {target_total}"
            ),
            inline=True
        )
        
        # Add similarity score
        embed.add_field(
            name="Mood Sync Score",
            value=f"{round(similarity)}% similar mood patterns",
            inline=False
        )
        
        # Add footer
        embed.set_footer(text="Based on mood entries from the last 30 days")
        
        await ctx.send(embed=embed)
        
    @commands.command(name="suggestactivity")
    async def suggest_activity(self, ctx, mood_type=None):
        """Get mood-based activity suggestions
        
        Examples:
        !suggestactivity
        !suggestactivity positive
        !suggestactivity negative
        !suggestactivity neutral
        """
        # If no mood specified, try to get the user's most recent mood
        if not mood_type:
            recent_moods = self._get_user_moods(ctx.author.id, days=3)  # Last 3 days
            
            if recent_moods:
                # Use the most recent mood
                mood_type = recent_moods[0]["category"]
                mood_desc = recent_moods[0]["description"]
            else:
                # Default to neutral if no recent moods
                mood_type = "neutral"
                mood_desc = "unknown"
        else:
            # Normalize input
            mood_type = mood_type.lower()
            if mood_type not in ["positive", "neutral", "negative"]:
                # Map common words to mood categories
                mood_map = {
                    "happy": "positive", "good": "positive", "great": "positive", "excited": "positive",
                    "okay": "neutral", "fine": "neutral", "alright": "neutral", "meh": "neutral",
                    "sad": "negative", "bad": "negative", "down": "negative", "anxious": "negative", "depressed": "negative"
                }
                mood_type = mood_map.get(mood_type, "neutral")
            mood_desc = mood_type
        
        # Activity suggestions based on mood
        activities = {
            "positive": [
                {"type": "Music", "suggestion": "Upbeat playlist to keep your good mood going", "link": "https://open.spotify.com/playlist/37i9dQZF1DX3rxVfibe1L0"},
                {"type": "Activity", "suggestion": "Channel your positive energy into a creative project", "link": None},
                {"type": "Exercise", "suggestion": "Try a fun dance workout to boost your mood even more", "link": "https://www.youtube.com/results?search_query=fun+dance+workout"},
                {"type": "Mindfulness", "suggestion": "Practice gratitude meditation to appreciate this moment", "link": "https://www.youtube.com/results?search_query=gratitude+meditation"},
                {"type": "Social", "suggestion": "Share your positive energy by connecting with a friend", "link": None}
            ],
            "neutral": [
                {"type": "Music", "suggestion": "Calming instrumental playlist to help you relax", "link": "https://open.spotify.com/playlist/37i9dQZF1DWZqd5JICZI0u"},
                {"type": "Activity", "suggestion": "Try a new hobby or activity that interests you", "link": None},
                {"type": "Exercise", "suggestion": "Take a walk outside to clear your mind", "link": None},
                {"type": "Mindfulness", "suggestion": "Try this 5-minute breathing exercise for balance", "link": "https://www.youtube.com/results?search_query=5+minute+breathing+exercise"},
                {"type": "Self-care", "suggestion": "Make yourself a soothing cup of tea and take a moment for yourself", "link": None}
            ],
            "negative": [
                {"type": "Music", "suggestion": "Calming playlist to help soothe difficult emotions", "link": "https://open.spotify.com/playlist/37i9dQZF1DWXe9gFZP0gtP"},
                {"type": "Activity", "suggestion": "Write down your thoughts in a journal to process them", "link": None},
                {"type": "Exercise", "suggestion": "Try this gentle yoga session for stress relief", "link": "https://www.youtube.com/results?search_query=gentle+yoga+for+stress"},
                {"type": "Mindfulness", "suggestion": "Practice this grounding exercise: name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, and 1 you can taste", "link": None},
                {"type": "Self-care", "suggestion": "Take a warm shower or bath to help relax your body", "link": None}
            ]
        }
        
        # Select 3 random activities from the appropriate mood category
        selected_activities = random.sample(activities[mood_type], 3)
        
        # Create embed
        embed = discord.Embed(
            title="🎶 Activity Suggestions",
            description=f"Based on your {mood_desc} mood, here are some activities that might help:",
            color=discord.Color.gold() if mood_type == "positive" else discord.Color.blue() if mood_type == "neutral" else discord.Color.dark_purple()
        )
        
        # Add activities to embed
        for activity in selected_activities:
            value = activity["suggestion"]
            if activity["link"]:
                value += f"\n[Click here]({activity['link']})"
                
            embed.add_field(
                name=f"📌 {activity['type']}",
                value=value,
                inline=False
            )
        
        # Add a breathing exercise for all moods
        embed.add_field(
            name="🌬️ Quick Breathing Exercise",
            value="Breathe in for 4 seconds, hold for 4 seconds, exhale for 6 seconds. Repeat 5 times.",
            inline=False
        )
        
        # Add footer
        embed.set_footer(text="Remember that it's okay to seek professional help if you're struggling")
        
        await ctx.send(embed=embed)
        
    @commands.command(name="deletelog")
    async def delete_log(self, ctx):
        """Delete your mood history
        
        This will permanently delete all your mood entries.
        You will be asked to confirm with a reaction.
        """
        user_id = str(ctx.author.id)
        
        # Check if user has any mood entries
        if not os.path.exists(self.moods_path):
            await ctx.send("❌ You don't have any mood entries to delete.")
            return
            
        with open(self.moods_path, "r") as f:
            moods = json.load(f)
            
        if user_id not in moods or not moods[user_id]:
            await ctx.send("❌ You don't have any mood entries to delete.")
            return
            
        # Ask for confirmation
        confirm_msg = await ctx.send(
            f"⚠️ **Warning**: This will permanently delete all your mood history. " 
            f"React with ✅ to confirm or ❌ to cancel."
        )
        
        # Add reaction options
        await confirm_msg.add_reaction("✅")  # Checkmark
        await confirm_msg.add_reaction("❌")  # X mark
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
        try:
            # Wait for user reaction
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Delete the user's mood entries
                del moods[user_id]
                
                # Save updated moods
                with open(self.moods_path, "w") as f:
                    json.dump(moods, f, indent=4)
                    
                await ctx.send("✅ Your mood history has been permanently deleted.")
            else:
                await ctx.send("❌ Deletion cancelled. Your mood history is safe.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Confirmation timed out. Your mood history was not deleted.")
        
        # Try to delete the confirmation message
        try:
            await confirm_msg.delete()
        except:
            pass

    
    async def check_reminders(self):
        """Background task to check and send reminders"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Load reminders
                if os.path.exists(self.reminders_path):
                    with open(self.reminders_path, "r") as f:
                        reminders = json.load(f)
                    
                    now = datetime.now()
                    current_time = now.strftime("%H:%M")
                    
                    for user_id, reminder in reminders.items():
                        # Check if it's time to send a reminder
                        if reminder["time"] == current_time:
                            # For daily reminders, always send
                            # For weekly reminders, check if it's been a week
                            should_remind = False
                            
                            if reminder["frequency"] == "daily":
                                should_remind = True
                            elif reminder["frequency"] == "weekly" and reminder["last_reminded"]:
                                last_reminded = datetime.fromisoformat(reminder["last_reminded"])
                                if (now - last_reminded).days >= 7:
                                    should_remind = True
                            elif reminder["frequency"] == "weekly" and not reminder["last_reminded"]:
                                should_remind = True
                            
                            if should_remind:
                                try:
                                    # Try to get the user
                                    user = await self.bot.fetch_user(int(user_id))
                                    channel = self.bot.get_channel(reminder["channel_id"])
                                    
                                    if channel:
                                        await channel.send(
                                            f"🧠 {user.mention} It's time for your mental health check-in! " 
                                            f"Use `!checkin` to start or `!prompt` for a reflection prompt."
                                        )
                                    else:
                                        # Try to DM if channel not found
                                        await user.send(
                                            f"🧠 It's time for your mental health check-in! " 
                                            f"Use `!checkin` to start or `!prompt` for a reflection prompt."
                                        )
                                    
                                    # Update last reminded time
                                    reminders[user_id]["last_reminded"] = now.isoformat()
                                    with open(self.reminders_path, "w") as f:
                                        json.dump(reminders, f, indent=4)
                                        
                                except Exception as e:
                                    print(f"Error sending reminder to {user_id}: {e}")
            except Exception as e:
                print(f"Error in check_reminders task: {e}")
            
            # Check every minute
            await asyncio.sleep(60)

async def setup(bot):
    await bot.add_cog(MentalHealth(bot))
