import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime
from typing import Optional

class Welcome(commands.Cog):
    """Welcome message system with beautiful embeds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/welcome_config.json"
        self.config = self.load_config()
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
    
    def load_config(self):
        """Load welcome configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading welcome config: {str(e)}")
            return {}
    
    def save_config(self):
        """Save welcome configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving welcome config: {str(e)}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send welcome message when a member joins"""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.config:
            return
            
        if not self.config[guild_id]["enabled"]:
            return
            
        channel_id = self.config[guild_id]["channel_id"]
        channel = self.bot.get_channel(int(channel_id))
        
        if not channel:
            return
            
        await self.send_welcome_message(channel, member)
    
    async def send_welcome_message(self, channel, member):
        """Send a beautiful welcome embed"""
        guild = member.guild
        
        # Get member count
        member_count = len([m for m in guild.members if not m.bot])
        bot_count = len([m for m in guild.members if m.bot])
        
        # Choose a random color for the embed
        colors = [
            discord.Color.brand_red(),
            discord.Color.brand_green(),
            discord.Color.brand_blue(),
            discord.Color.purple(),
            discord.Color.gold(),
            discord.Color.teal()
        ]
        color = random.choice(colors)
        
        # Create the embed
        embed = discord.Embed(
            title=f"Welcome to {guild.name}!",
            description=f"Hey {member.mention}, welcome to our community! We're excited to have you join us.",
            color=color,
            timestamp=datetime.now()
        )
        
        # Add server icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Add member avatar
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        
        # Add member information
        embed.add_field(
            name="📊 Server Stats",
            value=f"👥 Members: {member_count}\n🤖 Bots: {bot_count}",
            inline=True
        )
        
        # Add account creation date
        created_at = int(member.created_at.timestamp())
        embed.add_field(
            name="🗓️ Account Created",
            value=f"<t:{created_at}:R>",
            inline=True
        )
        
        # Add footer with member count
        embed.set_footer(text=f"Member #{member_count} • ID: {member.id}")
        
        # Add a decorative image based on server type or theme
        # This could be expanded with more options based on server name/theme
        banner_images = [
            "https://i.imgur.com/6YToyEF.png",  # Generic welcome banner
            "https://i.imgur.com/7K4pRYj.png",  # Community banner
            "https://i.imgur.com/JzDnCYJ.png",  # Gaming banner
            "https://i.imgur.com/2JL4Dao.png"   # Creative banner
        ]
        embed.set_image(url=random.choice(banner_images))
        
        await channel.send(embed=embed)
    
    @commands.command(name="enablewelcome")
    @commands.has_permissions(administrator=True)
    async def enable_welcome(self, ctx):
        """Enable welcome messages for this server"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {
                "enabled": True,
                "channel_id": str(ctx.channel.id)
            }
        else:
            self.config[guild_id]["enabled"] = True
        
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Welcome Messages Enabled",
            description=f"Welcome messages will be sent in <#{ctx.channel.id}>.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def set_welcome(self, ctx, channel_id: str):
        """Set the channel for welcome messages"""
        guild_id = str(ctx.guild.id)
        
        try:
            # Check if the channel exists
            channel = ctx.guild.get_channel(int(channel_id))
            if not channel:
                raise ValueError("Channel not found")
                
            if guild_id not in self.config:
                self.config[guild_id] = {
                    "enabled": True,
                    "channel_id": channel_id
                }
            else:
                self.config[guild_id]["channel_id"] = channel_id
                
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Welcome Channel Set",
                description=f"Welcome messages will be sent in <#{channel_id}>.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send("❌ Invalid channel ID. Please provide a valid channel ID.")
    
    @commands.command(name="testwelcome")
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Test the welcome message"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config or not self.config[guild_id]["enabled"]:
            await ctx.send("❌ Welcome messages are not enabled for this server.")
            return
            
        channel_id = self.config[guild_id]["channel_id"]
        channel = self.bot.get_channel(int(channel_id))
        
        if not channel:
            await ctx.send("❌ Welcome channel not found. Please set a valid channel.")
            return
            
        await self.send_welcome_message(channel, ctx.author)
        
        await ctx.send(f"✅ Test welcome message sent to <#{channel_id}>.")
    
    @commands.command(name="disablewelcome")
    @commands.has_permissions(administrator=True)
    async def disable_welcome(self, ctx):
        """Disable welcome messages for this server"""
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.config:
            self.config[guild_id]["enabled"] = False
            self.save_config()
            
        embed = discord.Embed(
            title="❌ Welcome Messages Disabled",
            description="Welcome messages have been disabled for this server.",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
