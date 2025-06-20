import discord
from discord.ext import commands
import asyncio
import json
import os
from typing import Dict, Optional

class StickyMessages(commands.Cog):
    """Sticky message management for Discord channels. This module allows moderators to create persistent messages that automatically reappear at the bottom of a channel after new messages are sent. Features include creating, removing, and listing sticky messages across multiple channels in a server, with beautiful embeds for better visibility."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sticky_data = {}
        self.data_file = "data/stickymessages.json"
        self.load_data()
        
    def load_data(self):
        """Load sticky message data from file"""
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    self.sticky_data = json.load(f)
        except Exception as e:
            print(f"Error loading sticky messages data: {e}")
            self.sticky_data = {}
            
    def save_data(self):
        """Save sticky message data to file"""
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.sticky_data, f, indent=4)
        except Exception as e:
            print(f"Error saving sticky messages data: {e}")
            
    def get_embed(self, content: str) -> discord.Embed:
        """Create a beautiful embed for sticky messages"""
        embed = discord.Embed(
            description=content,
            color=0x3498db
        )
        embed.set_footer(text="📌 Sticky Message")
        return embed
            
    @commands.group(name="sticky", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def sticky(self, ctx):
        """Sticky message commands"""
        embed = discord.Embed(
            title="📌 Sticky Messages",
            description="Commands for managing sticky messages",
            color=0x3498db
        )
        embed.add_field(
            name="Available Commands",
            value=(
                "`!sticky set <message>` - Set a sticky message in the current channel\n"
                "`!sticky remove` - Remove the sticky message from the current channel\n"
                "`!sticky list` - List all sticky messages in the server"
            ),
            inline=False
        )
        embed.set_footer(text="Sticky messages will reappear after new messages are sent")
        await ctx.send(embed=embed)
        
    @sticky.command(name="set")
    @commands.has_permissions(manage_messages=True)
    async def sticky_set(self, ctx, *, message: str):
        """Set a sticky message in the current channel"""
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        if guild_id not in self.sticky_data:
            self.sticky_data[guild_id] = {}
            
        embed = self.get_embed(message)
        sticky_msg = await ctx.send(embed=embed)
        
        self.sticky_data[guild_id][channel_id] = {
            "message": message,
            "last_message_id": sticky_msg.id
        }
        
        self.save_data()
        
        confirm_embed = discord.Embed(
            title="✅ Sticky Message Created",
            description=f"Successfully set a sticky message in {ctx.channel.mention}",
            color=0x2ecc71
        )
        confirm_embed.add_field(name="Message Content", value=message, inline=False)
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        await asyncio.sleep(5)
        try:
            await confirm_msg.delete()
        except:
            pass
            
    @sticky.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def sticky_remove(self, ctx):
        """Remove the sticky message from the current channel"""
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        if guild_id in self.sticky_data and channel_id in self.sticky_data[guild_id]:
            try:
                last_message_id = self.sticky_data[guild_id][channel_id]["last_message_id"]
                try:
                    last_message = await ctx.channel.fetch_message(last_message_id)
                    await last_message.delete()
                except:
                    pass  
            except:
                pass
                
            del self.sticky_data[guild_id][channel_id]
            
            if not self.sticky_data[guild_id]:
                del self.sticky_data[guild_id]
                
            self.save_data()
            
            embed = discord.Embed(
                title="✅ Sticky Message Removed",
                description=f"Successfully removed the sticky message from {ctx.channel.mention}",
                color=0x2ecc71
            )
            await ctx.send(embed=embed, delete_after=5)
        else:
            embed = discord.Embed(
                title="❌ No Sticky Message",
                description=f"There is no sticky message set in {ctx.channel.mention}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed, delete_after=5)
            
    @sticky.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def sticky_list(self, ctx):
        """List all sticky messages in the server"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.sticky_data or not self.sticky_data[guild_id]:
            embed = discord.Embed(
                title="📌 Sticky Messages",
                description="No sticky messages are set in this server",
                color=0xe74c3c
            )
            return await ctx.send(embed=embed)
            
        embed = discord.Embed(
            title="📌 Sticky Messages",
            description=f"List of all sticky messages in {ctx.guild.name}",
            color=0x3498db
        )
        
        for channel_id, data in self.sticky_data[guild_id].items():
            channel = self.bot.get_channel(int(channel_id))
            channel_name = f"#{channel.name}" if channel else f"Unknown Channel ({channel_id})"
            
            message = data["message"]
            if len(message) > 100:
                message = message[:97] + "..."
                
            embed.add_field(
                name=channel_name,
                value=message,
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listener for new messages to repost sticky messages"""
        if message.author.bot:
            return
            
        guild_id = str(message.guild.id) if message.guild else None
        channel_id = str(message.channel.id)
        
        if not guild_id or guild_id not in self.sticky_data or channel_id not in self.sticky_data[guild_id]:
            return
            
        sticky_data = self.sticky_data[guild_id][channel_id]
        
        try:
            last_message_id = sticky_data["last_message_id"]
            try:
                last_message = await message.channel.fetch_message(last_message_id)
                await last_message.delete()
            except:
                pass 
        except:
            pass
            
        embed = self.get_embed(sticky_data["message"])
        new_sticky = await message.channel.send(embed=embed)
        
        self.sticky_data[guild_id][channel_id]["last_message_id"] = new_sticky.id
        self.save_data()


async def setup(bot):
    await bot.add_cog(StickyMessages(bot))
