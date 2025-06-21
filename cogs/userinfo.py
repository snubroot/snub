import discord
from discord.ext import commands
import datetime
from typing import Optional
import os
import json

class UserInfo(commands.Cog):
    """Advanced user information system. This module provides detailed information about Discord users including account age, join date, roles, past warnings/mutes, and invite source."""
    
    def __init__(self, bot):
        self.bot = bot
        self.warnings_file = "data/warnings.json"
        self.mutes_file = "data/mutes.json"
        self.warnings_data = {}
        self.mutes_data = {}
        self.load_data()
        
    def load_data(self):
        """Load warnings and mutes data from files"""
        os.makedirs("data", exist_ok=True)
        
        # Load warnings data
        try:
            if os.path.exists(self.warnings_file):
                with open(self.warnings_file, "r") as f:
                    self.warnings_data = json.load(f)
        except Exception as e:
            print(f"Error loading warnings data: {e}")
            self.warnings_data = {}
            
        # Load mutes data
        try:
            if os.path.exists(self.mutes_file):
                with open(self.mutes_file, "r") as f:
                    self.mutes_data = json.load(f)
        except Exception as e:
            print(f"Error loading mutes data: {e}")
            self.mutes_data = {}
            
    def save_warnings_data(self):
        """Save warnings data to file"""
        os.makedirs(os.path.dirname(self.warnings_file), exist_ok=True)
        with open(self.warnings_file, "w") as f:
            json.dump(self.warnings_data, f, indent=4)
            
    def save_mutes_data(self):
        """Save mutes data to file"""
        os.makedirs(os.path.dirname(self.mutes_file), exist_ok=True)
        with open(self.mutes_file, "w") as f:
            json.dump(self.mutes_data, f, indent=4)
            
    def get_user_warnings(self, guild_id: int, user_id: int):
        """Get warnings for a user in a guild"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str not in self.warnings_data:
            return []
            
        if user_id_str not in self.warnings_data[guild_id_str]:
            return []
            
        return self.warnings_data[guild_id_str][user_id_str]
        
    def get_user_mutes(self, guild_id: int, user_id: int):
        """Get mutes for a user in a guild"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str not in self.mutes_data:
            return []
            
        if user_id_str not in self.mutes_data[guild_id_str]:
            return []
            
        return self.mutes_data[guild_id_str][user_id_str]
    
    @commands.command(name="userinfo")
    async def userinfo(self, ctx, user: Optional[discord.Member] = None):
        """Display detailed information about a user"""
        # If no user is specified, use the command author
        user = user or ctx.author
        
        # Create the embed
        embed = discord.Embed(
            title=f"User Information: {user.display_name}",
            color=user.color
        )
        
        # Add user avatar
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Account information
        created_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        account_age = (datetime.datetime.now(datetime.timezone.utc) - user.created_at).days
        
        embed.add_field(
            name="📅 Account Information",
            value=f"**Created:** {created_at}\n**Account Age:** {account_age} days",
            inline=False
        )
        
        # Server information
        joined_at = user.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC") if user.joined_at else "Unknown"
        join_age = (datetime.datetime.now(datetime.timezone.utc) - user.joined_at).days if user.joined_at else 0
        
        embed.add_field(
            name="🏠 Server Information",
            value=f"**Joined:** {joined_at}\n**Time in Server:** {join_age} days",
            inline=False
        )
        
        # Roles information
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        roles.reverse()  # Display highest roles first
        
        if roles:
            # Limit to first 15 roles to avoid embed field value limit
            roles_str = " ".join(roles[:15])
            if len(user.roles) > 16:  # +1 for @everyone which we excluded
                roles_str += f"\n*and {len(user.roles) - 16} more...*"
        else:
            roles_str = "No roles"
            
        embed.add_field(
            name=f"🎖️ Roles [{len(user.roles) - 1}]",
            value=roles_str,
            inline=False
        )
        
        # Warnings and mutes information
        warnings = self.get_user_warnings(ctx.guild.id, user.id)
        mutes = self.get_user_mutes(ctx.guild.id, user.id)
        
        moderation_str = ""
        if warnings:
            moderation_str += f"**Warnings:** {len(warnings)}\n"
        else:
            moderation_str += "**Warnings:** None\n"
            
        if mutes:
            moderation_str += f"**Past Mutes:** {len(mutes)}"
        else:
            moderation_str += "**Past Mutes:** None"
            
        embed.add_field(
            name="🔨 Moderation History",
            value=moderation_str,
            inline=False
        )
        
        # Try to get invite source
        try:
            invites_cog = self.bot.get_cog("Invites")
            if invites_cog:
                guild_id_str = str(ctx.guild.id)
                user_id_str = str(user.id)
                
                # Check if we have invite data for this guild and user
                if hasattr(invites_cog, "invites_data") and \
                   guild_id_str in invites_cog.invites_data and \
                   "inviter_map" in invites_cog.invites_data[guild_id_str] and \
                   user_id_str in invites_cog.invites_data[guild_id_str]["inviter_map"]:
                    
                    inviter_id = invites_cog.invites_data[guild_id_str]["inviter_map"][user_id_str]
                    inviter = ctx.guild.get_member(int(inviter_id))
                    
                    if inviter:
                        embed.add_field(
                            name="🔗 Invite Source",
                            value=f"Invited by {inviter.mention} ({inviter.display_name})",
                            inline=False
                        )
        except Exception as e:
            print(f"Error getting invite source: {e}")
        
        # Set footer and timestamp
        embed.set_footer(text=f"ID: {user.id} • Requested by {ctx.author.display_name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UserInfo(bot))
