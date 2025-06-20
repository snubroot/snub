import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import re

class CountdownCog(commands.Cog):
    """Real-time countdown timer system for tracking upcoming events. This module allows users to create dynamic countdowns to specific dates with custom event names. Features include automatic time updates, various date format parsing, and visual countdown displays that show days, hours, minutes, and seconds remaining until the target date."""
    def __init__(self, bot):
        self.bot = bot
        self.countdowns = {}
        self.countdown_tasks = {}
        
    @commands.command(name="countdown")
    async def countdown(self, ctx, *, date_str: str):
        try:
            target_date = self.parse_date(date_str)
            if not target_date:
                raise ValueError("Invalid date format")
                
            event_name = self.extract_event_name(date_str)
            
            embed = await self.create_countdown_embed(event_name, target_date)
            message = await ctx.send(embed=embed)
            
            countdown_id = str(message.id)
            self.countdowns[countdown_id] = {
                "channel_id": ctx.channel.id,
                "message_id": message.id,
                "target_date": target_date,
                "event_name": event_name
            }
            
            self.countdown_tasks[countdown_id] = self.bot.loop.create_task(
                self.update_countdown(countdown_id)
            )
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to set countdown: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    def parse_date(self, date_str):
        patterns = [
            r'(\d{4}-\d{2}-\d{2})', 
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                date_text = match.group(1)
                try:
                    if '-' in date_text:
                        return datetime.strptime(date_text, '%Y-%m-%d')
                    elif '/' in date_text:
                        return datetime.strptime(date_text, '%m/%d/%Y')
                    else:
                        return datetime.strptime(date_text, '%d %B %Y')
                except ValueError:
                    pass
        
        return None
    
    def extract_event_name(self, date_str):
        for separator in ["for", "to", "until", ":"]:
            if separator in date_str:
                parts = date_str.split(separator, 1)
                if len(parts) > 1 and parts[1].strip():
                    return parts[1].strip()
        
        return "Event"
    
    async def create_countdown_embed(self, event_name, target_date):
        now = datetime.now()
        time_left = target_date - now
        
        if time_left.total_seconds() <= 0:
            description = "This event has already occurred!"
            color = discord.Color.light_grey()
        else:
            days, remainder = divmod(time_left.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            description = f"**Time Remaining:**\n{int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"
            color = discord.Color.gold()
        
        embed = discord.Embed(
            title=f"⏱️ Countdown to {event_name}",
            description=description,
            color=color
        )
        
        embed.add_field(
            name="Target Date",
            value=target_date.strftime("%A, %B %d, %Y"),
            inline=True
        )
        
        embed.set_footer(text="Countdown updates in real-time")
        embed.timestamp = datetime.now()
        
        return embed
    
    async def update_countdown(self, countdown_id):
        try:
            countdown_data = self.countdowns[countdown_id]
            channel = self.bot.get_channel(countdown_data["channel_id"])
            
            if not channel:
                return
                
            try:
                message = await channel.fetch_message(countdown_data["message_id"])
            except discord.NotFound:
                return
            
            while True:
                now = datetime.now()
                target_date = countdown_data["target_date"]
                time_left = target_date - now
                
                if time_left.total_seconds() <= 0:
                    final_embed = discord.Embed(
                        title=f"⏱️ Countdown to {countdown_data['event_name']}",
                        description="**The event has arrived!**",
                        color=discord.Color.green()
                    )
                    final_embed.add_field(
                        name="Target Date",
                        value=target_date.strftime("%A, %B %d, %Y"),
                        inline=True
                    )
                    final_embed.set_footer(text="Countdown complete")
                    final_embed.timestamp = datetime.now()
                    
                    await message.edit(embed=final_embed)
                    break
                
                embed = await self.create_countdown_embed(
                    countdown_data["event_name"],
                    target_date
                )
                
                await message.edit(embed=embed)
                
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error updating countdown: {str(e)}")
        finally:
            if countdown_id in self.countdown_tasks:
                del self.countdown_tasks[countdown_id]
            if countdown_id in self.countdowns:
                del self.countdowns[countdown_id]

async def setup(bot):
    await bot.add_cog(CountdownCog(bot))
