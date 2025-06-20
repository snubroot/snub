import discord
from discord.ext import commands, tasks
import json
import os
import datetime
from typing import Optional
import asyncio

class Birthdays(commands.Cog):
    """Birthday tracking and celebration system. This module allows users to set and track birthdays within a server, with automatic birthday announcements, upcoming birthday notifications, and birthday listings. Features include setting, checking, and deleting birthdays, as well as viewing upcoming celebrations within a specified timeframe."""
    
    def __init__(self, bot):
        self.bot = bot
        self.birthdays_file = "data/birthdays.json"
        self.birthdays = {}
        self.load_birthdays()
        self.check_birthdays.start()
        
    def cog_unload(self):
        self.check_birthdays.cancel()
    
    def load_birthdays(self):
        os.makedirs(os.path.dirname(self.birthdays_file), exist_ok=True)
        try:
            if os.path.exists(self.birthdays_file):
                with open(self.birthdays_file, 'r') as f:
                    self.birthdays = json.load(f)
            else:
                self.birthdays = {}
                self.save_birthdays()
        except Exception as e:
            print(f"Error loading birthdays: {e}")
            self.birthdays = {}
    
    def save_birthdays(self):
        try:
            os.makedirs(os.path.dirname(self.birthdays_file), exist_ok=True)
            with open(self.birthdays_file, 'w') as f:
                json.dump(self.birthdays, f, indent=4)
        except Exception as e:
            print(f"Error saving birthdays: {e}")
    
    @staticmethod
    def get_month_name(month: int) -> str:
        months = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        return months.get(month, "Unknown")
    
    @staticmethod
    def add_suffix(day: int) -> str:
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    
    @staticmethod
    def format_birthday(day: int, month: int, year: int = None) -> str:
        day_with_suffix = Birthdays.add_suffix(day)
        month_name = Birthdays.get_month_name(month)
        if year:
            return f"{month_name} {day_with_suffix}, {year}"
        else:
            return f"{day_with_suffix} of {month_name}"
    
    @tasks.loop(hours=24)
    async def check_birthdays(self):
        await self.bot.wait_until_ready()
        
        today = datetime.datetime.now()
        current_month = today.month
        current_day = today.day
        
        for guild_id, guild_data in self.birthdays.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
                
            for user_id, birthday_data in guild_data.items():
                if birthday_data["month"] == current_month and birthday_data["day"] == current_day:
                    user = guild.get_member(int(user_id))
                    if user:
                        for channel in guild.text_channels:
                            if channel.permissions_for(guild.me).send_messages:
                                embed = discord.Embed(
                                    title="🎂 Happy Birthday!",
                                    description=f"Today is {user.mention}'s birthday! 🎉",
                                    color=discord.Color.gold()
                                )
                                embed.set_thumbnail(url=user.display_avatar.url)
                                embed.add_field(
                                    name="Birthday", 
                                    value=self.format_birthday(birthday_data["day"], birthday_data["month"]),
                                    inline=False
                                )
                                embed.set_footer(text=f"Wishing you an amazing day, {user.name}!")
                                
                                await channel.send(embed=embed)
                                break
    
    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        
        target_time = datetime.time(hour=9, minute=0)
        tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), target_time)
        
        if now.time() >= target_time:
            seconds_until_target = (tomorrow - now).total_seconds()
        else:
            target_today = datetime.datetime.combine(now.date(), target_time)
            seconds_until_target = (target_today - now).total_seconds()
            
        await asyncio.sleep(seconds_until_target)
    
    @commands.command(name="birthday-set", aliases=["setbirthday", "bdayset"])
    async def birthday_set(self, ctx, *, date_str: str = None):
        """Set your birthday
        
        Usage: !birthday-set MM/DD
        Example: !birthday-set 12/23
        """
        if not date_str:
            embed = discord.Embed(
                title="❌ Error",
                description="Please provide your birthday in MM/DD format.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Example", 
                value="!birthday-set 12/23",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        try:
            parts = date_str.strip().split('/')
            if len(parts) != 2:
                raise ValueError("Invalid date format")
                
            month = int(parts[0])
            day = int(parts[1])
            
            # Validate the date 
            if month < 1 or month > 12:
                raise ValueError("Invalid month")
                
            if day < 1 or day > 31:
                raise ValueError("Invalid day")
                
            if month in [4, 6, 9, 11] and day > 30:
                raise ValueError("This month only has 30 days")
                
            if month == 2 and day > 29:
                raise ValueError("February can have at most 29 days")
            
            formatted_birthday = self.format_birthday(day, month)
            
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Invalid date: {str(e)}. Please use MM/DD format.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Example", 
                value="!birthday-set 12/23",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        if guild_id not in self.birthdays:
            self.birthdays[guild_id] = {}
            
        self.birthdays[guild_id][user_id] = {
            "day": day,
            "month": month,
            "formatted": formatted_birthday
        }
        
        self.save_birthdays()
        
        embed = discord.Embed(
            title="🎂 Birthday Set",
            description=f"Your birthday has been set to **{formatted_birthday}**!",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Day", value=str(day), inline=True)
        embed.add_field(name="Month", value=self.get_month_name(month), inline=True)
        embed.set_footer(text="You'll receive birthday wishes when your special day arrives!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="birthday-check", aliases=["checkbirthday", "bdaycheck"])
    async def birthday_check(self, ctx, user: Optional[discord.Member] = None):
        """Check your birthday or someone else's birthday
        
        Usage: !birthday-check [user]
        Example: !birthday-check @username
        """
        target_user = user or ctx.author
        guild_id = str(ctx.guild.id)
        user_id = str(target_user.id)
        
        if guild_id not in self.birthdays or user_id not in self.birthdays[guild_id]:
            embed = discord.Embed(
                title="❓ No Birthday Found",
                description=f"{'You have not' if target_user == ctx.author else target_user.name + ' has not'} set a birthday yet.",
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.add_field(
                name="Set a Birthday", 
                value="Use `!birthday-set <day> <month>` to set your birthday!",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        birthday_data = self.birthdays[guild_id][user_id]
        formatted_birthday = birthday_data["formatted"]
        
        today = datetime.datetime.now().date()
        birthday_date = datetime.date(today.year, birthday_data["month"], birthday_data["day"])
        
        if birthday_date < today:
            birthday_date = datetime.date(today.year + 1, birthday_data["month"], birthday_data["day"])
            
        days_until = (birthday_date - today).days
        
        embed = discord.Embed(
            title=f"🎂 {'Your' if target_user == ctx.author else target_user.name + 's'} Birthday",
            description=f"**{formatted_birthday}**",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        if days_until == 0:
            embed.add_field(
                name="🎉 Today's the day!", 
                value="Happy Birthday! 🎈🎁🎊",
                inline=False
            )
        else:
            embed.add_field(
                name="⏱️ Countdown", 
                value=f"**{days_until}** days until {'your' if target_user == ctx.author else 'their'} next birthday!",
                inline=False
            )
            
        embed.set_footer(text=f"Birthday set for {target_user.name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="birthday-delete", aliases=["deletebirthday", "bdaydelete"])
    async def birthday_delete(self, ctx):
        """Delete your birthday information
        
        Usage: !birthday-delete
        """
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        if guild_id not in self.birthdays or user_id not in self.birthdays[guild_id]:
            embed = discord.Embed(
                title="❓ No Birthday Found",
                description="You don't have a birthday set to delete.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        del self.birthdays[guild_id][user_id]
        
        if not self.birthdays[guild_id]:
            del self.birthdays[guild_id]
            
        self.save_birthdays()
        
        embed = discord.Embed(
            title="🗑️ Birthday Deleted",
            description="Your birthday information has been deleted successfully.",
            color=discord.Color.brand_red()
        )
        embed.set_footer(text="You can set a new birthday anytime with !birthday-set")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="birthday-list", aliases=["listbirthdays", "bdaylist"])
    async def birthday_list(self, ctx):
        """List all birthdays in the server
        
        Usage: !birthday-list
        """
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.birthdays or not self.birthdays[guild_id]:
            embed = discord.Embed(
                title="📅 Birthday List",
                description="No birthdays have been set in this server yet.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Be the first to set your birthday with !birthday-set!")
            await ctx.send(embed=embed)
            return
        
        birthdays_list = []
        for user_id, birthday_data in self.birthdays[guild_id].items():
            user = ctx.guild.get_member(int(user_id))
            if user:
                birthdays_list.append({
                    "user": user,
                    "day": birthday_data["day"],
                    "month": birthday_data["month"],
                    "formatted": birthday_data["formatted"]
                })
        
        birthdays_list.sort(key=lambda x: (x["month"], x["day"]))
        
        embed = discord.Embed(
            title="🎂 Server Birthday List",
            description=f"There are **{len(birthdays_list)}** birthdays set in this server.",
            color=discord.Color.purple()
        )
        
        current_month = None
        month_entries = []
        
        for birthday in birthdays_list:
            if birthday["month"] != current_month:
                if month_entries:
                    embed.add_field(
                        name=f"📆 {self.get_month_name(current_month)}",
                        value="\n".join(month_entries),
                        inline=False
                    )
                    month_entries = []
                
                current_month = birthday["month"]
            
            day_with_suffix = self.add_suffix(birthday["day"])
            month_entries.append(f"**{day_with_suffix}** - {birthday['user'].mention}")
        
        if month_entries:
            embed.add_field(
                name=f"📆 {self.get_month_name(current_month)}",
                value="\n".join(month_entries),
                inline=False
            )
        
        embed.set_footer(text=f"Use !birthday-check @user to see more details about someone's birthday")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="birthday-upcoming", aliases=["upcomingbirthdays", "bdayupcoming"])
    async def birthday_upcoming(self, ctx, days: int = 30):
        """Show upcoming birthdays within a specified number of days
        
        Usage: !birthday-upcoming [days]
        Example: !birthday-upcoming 14 (shows birthdays in the next 14 days)
        """
        guild_id = str(ctx.guild.id)
        today = datetime.datetime.now().date()
        
        if guild_id not in self.birthdays or not self.birthdays[guild_id]:
            embed = discord.Embed(
                title="📅 Upcoming Birthdays",
                description="No birthdays have been set in this server yet.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Be the first to set your birthday with !birthday-set!")
            await ctx.send(embed=embed)
            return
        
        upcoming_birthdays = []
        for user_id, birthday_data in self.birthdays[guild_id].items():
            user = ctx.guild.get_member(int(user_id))
            if not user:
                continue
                
            try:
                birthday_date = datetime.date(today.year, birthday_data["month"], birthday_data["day"])
                
                if birthday_date < today:
                    birthday_date = datetime.date(today.year + 1, birthday_data["month"], birthday_data["day"])
                    
                days_until = (birthday_date - today).days
                
                if days_until <= days:
                    upcoming_birthdays.append({
                        "user": user,
                        "days_until": days_until,
                        "date": birthday_date,
                        "formatted": birthday_data["formatted"]
                    })
            except ValueError:
                continue
        
        upcoming_birthdays.sort(key=lambda x: x["days_until"])
        
        embed = discord.Embed(
            title="🎉 Upcoming Birthdays",
            description=f"Birthdays coming up in the next **{days} days**.",
            color=discord.Color.gold()
        )
        
        if not upcoming_birthdays:
            embed.add_field(
                name="No Upcoming Birthdays",
                value=f"There are no birthdays in the next {days} days.",
                inline=False
            )
        else:
            today_birthdays = []
            this_week = []
            this_month = []
            
            for birthday in upcoming_birthdays:
                if birthday["days_until"] == 0:
                    today_birthdays.append(birthday)
                elif birthday["days_until"] <= 7:
                    this_week.append(birthday)
                else:
                    this_month.append(birthday)
            
            if today_birthdays:
                today_list = [f"🎂 {b['user'].mention} - **TODAY!**" for b in today_birthdays]
                embed.add_field(
                    name="🎁 Celebrate Today!",
                    value="\n".join(today_list),
                    inline=False
                )
            
            if this_week:
                week_list = [f"🕙 {b['user'].mention} - **{b['days_until']}** day{'s' if b['days_until'] > 1 else ''} from now ({b['date'].strftime('%b %d')})" for b in this_week]
                embed.add_field(
                    name="📆 Coming This Week",
                    value="\n".join(week_list),
                    inline=False
                )
            
            if this_month:
                month_list = [f"📅 {b['user'].mention} - **{b['days_until']}** days from now ({b['date'].strftime('%b %d')})" for b in this_month]
                embed.add_field(
                    name="🗓 Coming Soon",
                    value="\n".join(month_list[:10]),
                    inline=False
                )
                
                if len(month_list) > 10:
                    embed.set_footer(text=f"And {len(month_list) - 10} more... Use !birthday-list to see all birthdays.")
                else:
                    embed.set_footer(text="Use !birthday-check @user to see more details about someone's birthday.")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Birthdays(bot))
