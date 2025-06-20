import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os
import asyncio
from typing import Dict, List, Tuple, Any, Optional

REACTION_ROLES_FILE = "data/reaction_roles.json"

class ReactionRoleView(discord.ui.View):
    def __init__(self, roles_data: Dict[str, List], guild: discord.Guild):
        super().__init__(timeout=None)
        
        self.roles_data = roles_data
        self.guild = guild
        
        for emoji_key, role_info in roles_data.items():
            role_id = role_info[0]
            emoji_data = role_info[1]
            
            button = discord.ui.Button(
                emoji=emoji_data["raw"],
                custom_id=f"reaction_role:{emoji_key}:{role_id}"
            )
            button.callback = self.button_callback
            self.add_item(button)
    
    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        _, emoji_key, role_id = custom_id.split(":")
        
        role = interaction.guild.get_role(int(role_id))
        if not role:
            await interaction.response.send_message("Role not found. It may have been deleted.", ephemeral=True)
            return
            
        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"Removed role: {role.name}", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"Added role: {role.name}", ephemeral=True)


class ReactionRoleSelect(discord.ui.Select):
    def __init__(self, roles_data: Dict[str, List], guild: discord.Guild):
        self.roles_data = roles_data
        self.guild = guild
        
        options = []
        for emoji_key, role_info in roles_data.items():
            role_id = role_info[0]
            emoji_data = role_info[1]
            
            # Get the role
            role = guild.get_role(int(role_id))
            if role:
                options.append(
                    discord.SelectOption(
                        label=role.name,
                        description=f"Add or remove the role {role.name}",
                        emoji=emoji_data["raw"],
                        value=f"{emoji_key}:{role_id}"
                    )
                )
        
        super().__init__(
            placeholder="❌ Nothing selected",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="reaction_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        emoji_key, role_id = value.split(":")
        
        role = interaction.guild.get_role(int(role_id))
        if not role:
            await interaction.response.send_message("Role not found. It may have been deleted.", ephemeral=True)
            return
            
        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"Removed role: {role.name}", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"Added role: {role.name}", ephemeral=True)


class ReactionRoleSelectView(discord.ui.View):
    def __init__(self, roles_data: Dict[str, List], guild: discord.Guild):
        super().__init__(timeout=None)
        self.add_item(ReactionRoleSelect(roles_data, guild))


class ReactionRoles(commands.Cog):
    """Reaction roles system for self-assignable roles. This module allows server administrators to create interactive role menus where users can assign themselves roles by clicking on buttons or selecting from dropdowns. Features include customizable role categories, emoji associations, and both button and dropdown menu interfaces."""
    
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles_data = self._load_reaction_roles_data()
        
        bot.loop.create_task(self._register_views())
    
    async def _register_views(self):
        await self.bot.wait_until_ready()
        
        for guild_id, categories in self.reaction_roles_data.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
                
            for category, data in categories.items():
                if "message_id" in data and "channel_id" in data and "roles" in data:
                    if data.get("panel_type") == "button":
                        self.bot.add_view(ReactionRoleView(data["roles"], guild), message_id=data["message_id"])
                    elif data.get("panel_type") == "menu":
                        self.bot.add_view(ReactionRoleSelectView(data["roles"], guild), message_id=data["message_id"])
    
    def _load_reaction_roles_data(self) -> Dict[str, Any]:
        """Load reaction roles data from file"""
        if not os.path.exists("data"):
            os.makedirs("data")
            
        if not os.path.exists(REACTION_ROLES_FILE):
            return {}
            
        try:
            with open(REACTION_ROLES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading reaction roles data: {e}")
            return {}
    
    def _save_reaction_roles_data(self) -> None:
        """Save reaction roles data to file"""
        if not os.path.exists("data"):
            os.makedirs("data")
            
        try:
            with open(REACTION_ROLES_FILE, "w") as f:
                json.dump(self.reaction_roles_data, f, indent=4)
        except Exception as e:
            print(f"Error saving reaction roles data: {e}")
    
    @app_commands.command(name="reactionrole-add", description="Add a role to a reaction role category")
    @app_commands.describe(
        category="The category name for the reaction role",
        role="The role to assign",
        emoji="The emoji to use for the reaction"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def add_reaction_role(self, interaction: discord.Interaction, category: str, role: discord.Role, emoji: str):
        """Add a role to a reaction role category"""
        try:
            discord_emoji = discord.PartialEmoji.from_str(emoji)
            emoji_data = {
                "id": str(discord_emoji.id) if discord_emoji.id else None,
                "name": discord_emoji.name,
                "raw": emoji
            }
        except:
            emoji_data = {
                "id": None,
                "name": emoji,
                "raw": emoji
            }
        
        guild_id = str(interaction.guild.id)
        if guild_id not in self.reaction_roles_data:
            self.reaction_roles_data[guild_id] = {}
        
        if category not in self.reaction_roles_data[guild_id]:
            self.reaction_roles_data[guild_id][category] = {
                "roles": {},
                "message_id": None,
                "channel_id": None
            }
        
        self.reaction_roles_data[guild_id][category]["roles"][emoji] = [
            str(role.id),
            emoji_data
        ]
        
        self._save_reaction_roles_data()
        
        embed = discord.Embed(
            title="✅ Reaction Role Added",
            description=f"Successfully added role {role.mention} with emoji {emoji} to category **{category}**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📘 Button Panel",
            value=f"Use `/reactionrole-button {category}` to create a button panel",
            inline=True
        )
        
        embed.add_field(
            name="📘 Menu Panel",
            value=f"Use `/reactionrole-menu {category}` to create a dropdown menu panel",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reactionrole-button", description="Create a button panel for a reaction role category")
    @app_commands.describe(
        category="The category name for the reaction role",
        channel="The channel to send the panel to (defaults to current channel)"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def button_panel(self, interaction: discord.Interaction, category: str, channel: Optional[discord.TextChannel] = None):
        """Create a button panel for a reaction role category"""
        target_channel = channel or interaction.channel
        
        guild_id = str(interaction.guild.id)
        if guild_id not in self.reaction_roles_data or category not in self.reaction_roles_data[guild_id]:
            await interaction.response.send_message(f"Category **{category}** not found!", ephemeral=True)
            return
        
        category_data = self.reaction_roles_data[guild_id][category]
        
        if not category_data.get("roles"):
            await interaction.response.send_message(f"No roles found in category **{category}**!", ephemeral=True)
            return
        
        role_info = []
        for emoji_key, role_data in category_data["roles"].items():
            role_id = role_data[0]
            emoji_raw = role_data[1]["raw"]
            
            role = interaction.guild.get_role(int(role_id))
            if role:
                role_info.append(f"{emoji_raw} | {role.mention}")
        
        title_case_category = category.lower()
        title_case_category = title_case_category[0].upper() + title_case_category[1:]
        
        embed = discord.Embed(
            title=f"{title_case_category} Roles",
            description="Choose your roles by clicking the buttons below!\n\n" + "\n".join(role_info),
            color=discord.Color.blue()
        )
        
        view = ReactionRoleView(category_data["roles"], interaction.guild)
        
        await interaction.response.send_message("Creating reaction role panel...", ephemeral=True)
        message = await target_channel.send(embed=embed, view=view)
        
        category_data["message_id"] = message.id
        category_data["channel_id"] = target_channel.id
        category_data["panel_type"] = "button"
        category_data["message_id"] = message.id
        category_data["channel_id"] = target_channel.id
        category_data["panel_type"] = "button"
        self._save_reaction_roles_data()
        
        await interaction.edit_original_response(content="Reaction role panel created successfully!")
    
    @app_commands.command(name="reactionrole-menu", description="Create a dropdown menu panel for a reaction role category")
    @app_commands.describe(
        category="The category name for the reaction role",
        channel="The channel to send the panel to (defaults to current channel)"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def menu_panel(self, interaction: discord.Interaction, category: str, channel: Optional[discord.TextChannel] = None):
        """Create a dropdown menu panel for a reaction role category"""
        target_channel = channel or interaction.channel
        
        guild_id = str(interaction.guild.id)
        if guild_id not in self.reaction_roles_data or category not in self.reaction_roles_data[guild_id]:
            await interaction.response.send_message(f"Category **{category}** not found!", ephemeral=True)
            return
        
        category_data = self.reaction_roles_data[guild_id][category]
        
        if not category_data.get("roles"):
            await interaction.response.send_message(f"No roles found in category **{category}**!", ephemeral=True)
            return
        
        role_info = []
        for emoji_key, role_data in category_data["roles"].items():
            role_id = role_data[0]
            emoji_raw = role_data[1]["raw"]
            
            role = interaction.guild.get_role(int(role_id))
            if role:
                role_info.append(f"{emoji_raw} | {role.mention}")
        
        title_case_category = category.lower()
        title_case_category = title_case_category[0].upper() + title_case_category[1:]
        
        embed = discord.Embed(
            title=f"{title_case_category} Roles",
            description="Choose your roles from the dropdown menu below!\n\n" + "\n".join(role_info),
            color=discord.Color.blue()
        )
        
        view = ReactionRoleSelectView(category_data["roles"], interaction.guild)
        
        await interaction.response.send_message("Creating reaction role panel...", ephemeral=True)
        message = await target_channel.send(embed=embed, view=view)
        
        category_data["message_id"] = message.id
        category_data["channel_id"] = target_channel.id
        category_data["panel_type"] = "menu"
        self._save_reaction_roles_data()
        
        await interaction.edit_original_response(content="Reaction role panel created successfully!")
    
    @app_commands.command(name="reactionrole-list", description="List all reaction role categories")
    @app_commands.default_permissions(manage_roles=True)
    async def list_reaction_roles(self, interaction: discord.Interaction):
        """List all reaction role categories"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.reaction_roles_data or not self.reaction_roles_data[guild_id]:
            await interaction.response.send_message("No reaction role categories found!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📃 Reaction Role Categories",
            color=discord.Color.blue()
        )
        
        for i, (category, data) in enumerate(self.reaction_roles_data[guild_id].items(), 1):
            role_count = len(data.get("roles", {}))
            panel_type = data.get("panel_type", "None")
            
            embed.add_field(
                name=f"{i}. {category}",
                value=f"Roles: {role_count}\nPanel Type: {panel_type}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reactionrole-delete", description="Delete a reaction role category")
    @app_commands.describe(category="The category name to delete")
    @app_commands.default_permissions(manage_roles=True)
    async def delete_reaction_role(self, interaction: discord.Interaction, category: str):
        """Delete a reaction role category"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.reaction_roles_data or category not in self.reaction_roles_data[guild_id]:
            await interaction.response.send_message(f"Category **{category}** not found!", ephemeral=True)
            return
        
        del self.reaction_roles_data[guild_id][category]
        self._save_reaction_roles_data()
        
        await interaction.response.send_message(f"Category **{category}** deleted successfully!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
