import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from typing import Dict, Optional

VERIFICATION_CONFIG_FILE = "data/verification_config.json"

def load_verification_config() -> Dict:
    """Load verification configuration from file"""
    if not os.path.exists(VERIFICATION_CONFIG_FILE):
        # Create the data directory if it doesn't exist
        os.makedirs(os.path.dirname(VERIFICATION_CONFIG_FILE), exist_ok=True)
        return {}
    
    try:
        with open(VERIFICATION_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_verification_config(config: Dict) -> None:
    """Save verification configuration to file"""
    # Create the data directory if it doesn't exist
    os.makedirs(os.path.dirname(VERIFICATION_CONFIG_FILE), exist_ok=True)
    
    with open(VERIFICATION_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Add the verification button with a checkmark emoji
        verify_button = discord.ui.Button(
            emoji="✅",
            custom_id="verification:verify"
        )
        verify_button.callback = self.verify_callback
        self.add_item(verify_button)
    
    async def verify_callback(self, interaction: discord.Interaction):
        # Load the verification config
        config = load_verification_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config or not config[guild_id]["enabled"]:
            await interaction.response.send_message("Verification system is not enabled on this server.", ephemeral=True)
            return
            
        if "role_id" not in config[guild_id] or not config[guild_id]["role_id"]:
            await interaction.response.send_message("Verification role has not been set up. Please contact an administrator.", ephemeral=True)
            return
            
        role_id = int(config[guild_id]["role_id"])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("Verification role not found. It may have been deleted.", ephemeral=True)
            return
            
        member = interaction.user
        
        # Check if the user already has the role
        if role in member.roles:
            await interaction.response.send_message("You are already verified!", ephemeral=True)
            return
            
        # Add the verification role to the user
        try:
            await member.add_roles(role)
            await interaction.response.send_message("You have been successfully verified!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to assign roles. Please contact an administrator.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


class Verification(commands.Cog):
    """Verification system for new server members. This module allows server administrators to set up a verification system where users can verify themselves by reacting to a message and receive a role."""
    
    def __init__(self, bot):
        self.bot = bot
        self._register_views()
    
    def _register_views(self):
        """Register the verification view for persistent buttons"""
        self.bot.add_view(VerificationView())
    
    @commands.command(name="enableverify")
    @commands.has_permissions(administrator=True)
    async def enable_verify(self, ctx):
        """Enable the verification system for this server"""
        config = load_verification_config()
        guild_id = str(ctx.guild.id)
        
        if guild_id not in config:
            config[guild_id] = {}
            
        config[guild_id]["enabled"] = True
        save_verification_config(config)
        
        embed = discord.Embed(
            title="✅ Verification System Enabled",
            description="The verification system has been enabled for this server.\n\n" +
                      "Next steps:\n" +
                      "1. Set the verification channel with `!setverify <channel_id>`\n" +
                      "2. Set the verification role with `!setverifyrole <@role>`",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="disableverify")
    @commands.has_permissions(administrator=True)
    async def disable_verify(self, ctx):
        """Disable the verification system for this server"""
        config = load_verification_config()
        guild_id = str(ctx.guild.id)
        
        if guild_id in config:
            config[guild_id]["enabled"] = False
            save_verification_config(config)
            
        embed = discord.Embed(
            title="❌ Verification System Disabled",
            description="The verification system has been disabled for this server.",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="setverify")
    @commands.has_permissions(administrator=True)
    async def set_verify_channel(self, ctx, channel_id: str):
        """Set the channel where the verification embed will be posted"""
        config = load_verification_config()
        guild_id = str(ctx.guild.id)
        
        # Check if verification is enabled
        if guild_id not in config or not config[guild_id].get("enabled", False):
            embed = discord.Embed(
                title="❌ Error",
                description="The verification system is not enabled for this server.\n" +
                          "Please use `!enableverify` first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Validate channel ID
        try:
            channel_id = int(channel_id.strip('<>#'))
            channel = ctx.guild.get_channel(channel_id)
            
            if not channel:
                raise ValueError("Channel not found")
                
            if not isinstance(channel, discord.TextChannel):
                raise ValueError("Channel must be a text channel")
                
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Invalid channel: {str(e)}\n" +
                          "Please provide a valid text channel ID.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Update config
        config[guild_id]["channel_id"] = channel_id
        save_verification_config(config)
        
        embed = discord.Embed(
            title="✅ Verification Channel Set",
            description=f"Verification channel set to {channel.mention}.\n\n" +
                      "Next step:\n" +
                      "- Set the verification role with `!setverifyrole <@role>`\n\n" +
                      "Once both channel and role are set, the verification embed will be posted automatically.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        
        # Check if we can post the verification embed now
        if "role_id" in config[guild_id] and config[guild_id]["role_id"]:
            await self.post_verification_embed(ctx.guild, channel_id)
    
    @commands.command(name="setverifyrole")
    @commands.has_permissions(administrator=True)
    async def set_verify_role(self, ctx, role: discord.Role):
        """Set the role that users will receive upon verification"""
        config = load_verification_config()
        guild_id = str(ctx.guild.id)
        
        # Check if verification is enabled
        if guild_id not in config or not config[guild_id].get("enabled", False):
            embed = discord.Embed(
                title="❌ Error",
                description="The verification system is not enabled for this server.\n" +
                          "Please use `!enableverify` first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Update config
        config[guild_id]["role_id"] = role.id
        save_verification_config(config)
        
        embed = discord.Embed(
            title="✅ Verification Role Set",
            description=f"Verification role set to {role.mention}.\n\n" +
                      "Next step:\n" +
                      "- Set the verification channel with `!setverify <channel_id>` if you haven't already.\n\n" +
                      "Once both channel and role are set, the verification embed will be posted automatically.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        
        # Check if we can post the verification embed now
        if "channel_id" in config[guild_id] and config[guild_id]["channel_id"]:
            await self.post_verification_embed(ctx.guild, config[guild_id]["channel_id"])
    
    async def post_verification_embed(self, guild: discord.Guild, channel_id: int):
        """Post the verification embed in the specified channel"""
        config = load_verification_config()
        guild_id = str(guild.id)
        
        # Get the channel
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        # Check if there's already a message ID stored
        if "message_id" in config[guild_id]:
            try:
                # Try to fetch the existing message
                message = await channel.fetch_message(config[guild_id]["message_id"])
                # If we found it, no need to post a new one
                return
            except (discord.NotFound, discord.HTTPException):
                # Message was deleted or not found, continue to create a new one
                pass
        
        # Create a visually stunning embed
        embed = discord.Embed(
            title=f"Welcome to {guild.name}!",
            description="Thank you for joining our server! To gain access to all channels, please verify yourself by clicking the checkmark button below.",
            color=discord.Color.blue()
        )
        
        # Add server icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Add footer
        embed.set_footer(text="React with ✅ to verify and gain access!")
        
        # Create the view with the verification button
        view = VerificationView()
        
        # Send the embed
        message = await channel.send(embed=embed, view=view)
        
        # Store the message ID in the config
        config[guild_id]["message_id"] = message.id
        save_verification_config(config)

    @commands.Cog.listener()
    async def on_ready(self):
        """When the bot is ready, post verification embeds if needed"""
        config = load_verification_config()
        
        for guild_id, guild_config in config.items():
            if not guild_config.get("enabled", False):
                continue
                
            if "channel_id" not in guild_config or "role_id" not in guild_config:
                continue
                
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
                
            await self.post_verification_embed(guild, guild_config["channel_id"])


async def setup(bot):
    await bot.add_cog(Verification(bot))
