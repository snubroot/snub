import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from openai import OpenAI
import config
from typing import List, Dict, Optional, Literal, Union

class ServerBuilder(commands.Cog):
    """AI-powered Discord server builder that creates complete server structures in seconds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.templates_file = "data/server_templates.json"
        self.load_templates()
        self.pending_custom_inputs = {}
        
    def load_templates(self):
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, "r") as f:
                    self.templates = json.load(f)
            else:
                # Default templates
                self.templates = {}
                self.save_templates()
        except Exception as e:
            print(f"Error loading server templates: {e}")
            self.templates = {}
            
    def save_templates(self):
        try:
            with open(self.templates_file, "w") as f:
                json.dump(self.templates, f, indent=4)
        except Exception as e:
            print(f"Error saving server templates: {e}")
    
    async def _run_openai_call(self, func, *args, **kwargs):
        """Run an OpenAI API call in a thread to prevent blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: func(*args, **kwargs)
        )
    
    async def _generate_server_structure(self, server_type, member_scale, moderation_level, focus_areas, custom_input=None):
        """Generate server structure using OpenAI"""
        custom_description = ""
        custom_features = ""
        
        if custom_input:
            if custom_input.get("description"):
                custom_description = f"\nUser's server description: {custom_input['description']}"
            if custom_input.get("special_features"):
                custom_features = f"\nUser's requested special features: {custom_input['special_features']}"
        
        prompt = f"""
        Create a complete Discord server structure for a {server_type} server with {member_scale} expected members.
        Moderation level: {moderation_level}
        Focus areas: {', '.join(focus_areas)}{custom_description}{custom_features}
        
        Return a JSON structure with the following format:
        {{
            "categories": [
                {{
                    "name": "Category Name",
                    "permissions": {{}},
                    "channels": [
                        {{
                            "name": "channel-name",
                            "type": "text or voice",
                            "topic": "Channel topic/description",
                            "permissions": {{}}
                        }}
                    ]
                }}
            ],
            "roles": [
                {{
                    "name": "Role Name",
                    "permissions": {{}},
                    "color": [r, g, b],
                    "displayed_separately": true/false,
                    "mentionable": true/false
                }}
            ],
            "welcome_message": "Welcome message content",
            "rules": ["Rule 1", "Rule 2", ...],
            "recommended_bots": ["Bot 1", "Bot 2", ...],
            "emojis": ["emoji1", "emoji2", ...]
        }}
        
        Be creative but practical. Include all necessary channels for a {server_type} server.
        
        Use modern Discord naming conventions and structure:
        1. For categories, use ALL CAPS names like "INFORMATION", "COMMUNITY", "GAMING", "MEDIA", "VOICE CHANNELS"
        2. For channels, use lowercase with hyphens like "welcome", "server-rules", "general-chat"
        3. Use emojis at the start of channel names where appropriate like "📢-announcements", "🎮-gaming"
        4. Include forum channels where appropriate (specify with "type": "forum")
        5. Include stage channels for larger servers (specify with "type": "stage")
        6. Include thread-enabled text channels where appropriate
        7. Group similar channels under appropriate categories
        8. Create dedicated categories for voice channels
        9. For larger servers, include dedicated categories for community events and media sharing
        10. Include appropriate channels for bot commands and self-roles
        """
        
        try:
            response = await self._run_openai_call(
                self.openai_client.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert Discord server architect who designs optimal server structures."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from the response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            return json.loads(content)
        except Exception as e:
            raise Exception(f"Failed to generate server structure: {str(e)}")
    
    async def _set_permissions(self, channel_or_category, permissions_dict):
        """Set permissions for a channel or category"""
        try:
            for role, perms in permissions_dict.items():
                overwrite = discord.PermissionOverwrite(**perms)
                await channel_or_category.set_permissions(role, overwrite=overwrite)
        except Exception as e:
            # Log error but don't crash
            print(f"Error setting permissions: {e}")
    
    async def _create_channel(self, guild, category, channel_data):
        """Create a channel with the given data"""
        try:
            if channel_data["type"] == "text":
                channel = await guild.create_text_channel(
                    name=channel_data["name"],
                    topic=channel_data["topic"],
                    category=category,
                    permission_overwrites=channel_data["permissions"]
                )
            elif channel_data["type"] == "voice":
                channel = await guild.create_voice_channel(
                    name=channel_data["name"],
                    topic=channel_data["topic"],
                    category=category,
                    permission_overwrites=channel_data["permissions"]
                )
            elif channel_data["type"] == "forum":
                channel = await guild.create_forum(
                    name=channel_data["name"],
                    topic=channel_data["topic"],
                    category=category,
                    permission_overwrites=channel_data["permissions"]
                )
            elif channel_data["type"] == "stage":
                channel = await guild.create_stage_channel(
                    name=channel_data["name"],
                    topic=channel_data["topic"],
                    category=category,
                    permission_overwrites=channel_data["permissions"]
                )
            else:
                raise Exception(f"Unsupported channel type: {channel_data['type']}")
            
            return channel
        except Exception as e:
            raise Exception(f"Failed to create channel: {str(e)}")
    
    class ServerTypeSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Gaming",
                    description="For gaming communities and clans",
                    emoji="🎮",
                    value="gaming"
                ),
                discord.SelectOption(
                    label="Community",
                    description="For general community servers",
                    emoji="👥",
                    value="community"
                ),
                discord.SelectOption(
                    label="Education",
                    description="For learning and educational servers",
                    emoji="📚",
                    value="education"
                ),
                discord.SelectOption(
                    label="Business",
                    description="For professional and work-related servers",
                    emoji="💼",
                    value="business"
                ),
                discord.SelectOption(
                    label="Creative",
                    description="For art, music, and creative communities",
                    emoji="🎨",
                    value="creative"
                ),
                discord.SelectOption(
                    label="Tech",
                    description="For technology, programming, and development",
                    emoji="💻",
                    value="tech"
                ),
                discord.SelectOption(
                    label="Entertainment",
                    description="For media, streaming, and entertainment content",
                    emoji="🍿",
                    value="entertainment"
                ),
                discord.SelectOption(
                    label="Social",
                    description="For friends and social groups",
                    emoji="🌟",
                    value="social"
                )
            ]
            
            super().__init__(
                placeholder="Select server type...",
                min_values=1,
                max_values=1,
                options=options
            )
        
        async def callback(self, interaction):
            # Store the selection in the parent view
            self.view.server_type = self.values[0]
            
            # Enable the next select menu
            self.view.children[1].disabled = False
            
            # Update the message with both current and next step
            await interaction.response.edit_message(
                content=f"# 🏗️ AI Server Builder\n\n**Server type:** {self.values[0].title()}\n\nNow select the expected member scale:",
                view=self.view
            )
    
    class MemberScaleSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Small",
                    description="Up to 50 members",
                    emoji="🔹",
                    value="small"
                ),
                discord.SelectOption(
                    label="Medium",
                    description="50-500 members",
                    emoji="🔷",
                    value="medium"
                ),
                discord.SelectOption(
                    label="Large",
                    description="500-2000 members",
                    emoji="💠",
                    value="large"
                ),
                discord.SelectOption(
                    label="Massive",
                    description="2000+ members",
                    emoji="🌟",
                    value="massive"
                )
            ]
            
            super().__init__(
                placeholder="Select member scale...",
                min_values=1,
                max_values=1,
                options=options,
                disabled=True
            )
        
        async def callback(self, interaction):
            # Store the selection in the parent view
            self.view.member_scale = self.values[0]
            
            # Enable the next select menu
            self.view.children[2].disabled = False
            
            # Update the message with progress and next step
            await interaction.response.edit_message(
                content=f"# 🏗️ AI Server Builder\n\n**Server type:** {self.view.server_type.title()}\n**Member scale:** {self.values[0].title()}\n\nNow select the moderation level:",
                view=self.view
            )
    
    class ModerationSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Minimal",
                    description="Basic moderation, relaxed atmosphere",
                    emoji="🟢",
                    value="minimal"
                ),
                discord.SelectOption(
                    label="Standard",
                    description="Balanced moderation for most servers",
                    emoji="🟡",
                    value="standard"
                ),
                discord.SelectOption(
                    label="Strict",
                    description="Comprehensive moderation with detailed rules",
                    emoji="🟠",
                    value="strict"
                ),
                discord.SelectOption(
                    label="Professional",
                    description="Corporate-level moderation and structure",
                    emoji="🔴",
                    value="professional"
                )
            ]
            
            super().__init__(
                placeholder="Select moderation level...",
                min_values=1,
                max_values=1,
                options=options,
                disabled=True
            )
        
        async def callback(self, interaction):
            # Store the selection in the parent view
            self.view.moderation_level = self.values[0]
            
            # Enable the next select menu
            self.view.children[3].disabled = False
            
            # Update the message with progress and next step
            await interaction.response.edit_message(
                content=f"# 🏗️ AI Server Builder\n\n**Server type:** {self.view.server_type.title()}\n**Member scale:** {self.view.member_scale.title()}\n**Moderation level:** {self.values[0].title()}\n\nNow select focus areas (multiple allowed):",
                view=self.view
            )
    
    class FocusAreasSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="General Chat", value="general_chat", emoji="💬"),
                discord.SelectOption(label="Memes", value="memes", emoji="😂"),
                discord.SelectOption(label="News & Updates", value="news", emoji="📰"),
                discord.SelectOption(label="Gaming", value="gaming", emoji="🎮"),
                discord.SelectOption(label="Art & Design", value="art", emoji="🎨"),
                discord.SelectOption(label="Music", value="music", emoji="🎵"),
                discord.SelectOption(label="Programming", value="programming", emoji="💻"),
                discord.SelectOption(label="Education", value="education", emoji="📚"),
                discord.SelectOption(label="Events", value="events", emoji="📅"),
                discord.SelectOption(label="Streaming", value="streaming", emoji="📺"),
                discord.SelectOption(label="Politics", value="politics", emoji="🗳️"),
                discord.SelectOption(label="Sports", value="sports", emoji="⚽"),
                discord.SelectOption(label="Voice Channels", value="voice", emoji="🎤"),
                discord.SelectOption(label="Bot Commands", value="bot_commands", emoji="🤖"),
                discord.SelectOption(label="Announcements", value="announcements", emoji="📢"),
                discord.SelectOption(label="Self Roles", value="self_roles", emoji="🏷️"),
                discord.SelectOption(label="Media Sharing", value="media", emoji="📷"),
                discord.SelectOption(label="Collaborations", value="collaborations", emoji="🤝"),
                discord.SelectOption(label="Feedback", value="feedback", emoji="📝"),
                discord.SelectOption(label="Resources", value="resources", emoji="📌")
            ]
            
            super().__init__(
                placeholder="Select focus areas...",
                min_values=1,
                max_values=8,
                options=options,
                disabled=True
            )
        
        async def callback(self, interaction):
            # Store the selection in the parent view
            self.view.focus_areas = self.values
            
            # Format focus areas for display
            focus_areas_str = ", ".join([area.replace("_", " ").title() for area in self.values])
            
            # Enable the custom input button and build button
            self.view.children[4].disabled = False  # Custom input button
            self.view.children[5].disabled = False  # Build server button
            
            # Update the message with all selections and final step
            await interaction.response.edit_message(
                content=f"# 🏗️ AI Server Builder\n\n**Server type:** {self.view.server_type.title()}\n**Member scale:** {self.view.member_scale.title()}\n**Moderation level:** {self.view.moderation_level.title()}\n**Focus areas:** {focus_areas_str}\n\n✅ All options selected! You can now add custom input or build your server directly.",
                view=self.view
            )
    
    class CustomInputModal(discord.ui.Modal, title="Custom Server Input"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
        
        description = discord.ui.TextInput(
            label="Server Description",
            placeholder="Describe your server's purpose and community...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        
        special_features = discord.ui.TextInput(
            label="Special Features",
            placeholder="Any special features you'd like (e.g., unique channels, roles)...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            # Store the custom input in the cog
            self.cog.pending_custom_inputs[interaction.user.id] = {
                "description": self.description.value,
                "special_features": self.special_features.value
            }
            
            await interaction.response.send_message(
                "✅ Custom input received! Click the Build Server button when ready.",
                ephemeral=True
            )
    
    class CustomInputButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                label="Add Custom Input",
                emoji="✏️",
                disabled=True
            )
        
        async def callback(self, interaction):
            await interaction.response.send_modal(ServerBuilder.CustomInputModal(cog=self.view.cog))
    
    class BuildServerButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.primary,
                label="Build Server",
                emoji="🏗️",
                disabled=True
            )
        
        async def callback(self, interaction):
            await interaction.response.defer(thinking=True)
            
            try:
                # Get the parent cog
                server_builder = self.view.cog
                
                # Get any custom input if provided
                custom_input = server_builder.pending_custom_inputs.get(interaction.user.id, {})
                
                # Generate server structure
                server_structure = await server_builder._generate_server_structure(
                    self.view.server_type,
                    self.view.member_scale,
                    self.view.moderation_level,
                    self.view.focus_areas,
                    custom_input
                )
                
                # Start building the server
                await interaction.followup.send("🏗️ **Building your server...**")
                
                # Create categories and channels
                for category_data in server_structure["categories"]:
                    category = await interaction.guild.create_category(category_data["name"])
                    
                    # Create channels in this category
                    for channel_data in category_data["channels"]:
                        try:
                            channel_type = channel_data["type"]
                            
                            # Handle different channel types
                            if channel_type == "text":
                                channel = await category.create_text_channel(channel_data["name"])
                                if "topic" in channel_data:
                                    await channel.edit(topic=channel_data["topic"])
                            elif channel_type == "voice":
                                channel = await category.create_voice_channel(channel_data["name"])
                            # For forum and stage channels, check if the guild has the necessary features
                            elif channel_type == "forum" and "COMMUNITY" in interaction.guild.features:
                                # Fall back to text channel if forum creation fails
                                try:
                                    channel = await category.create_text_channel(channel_data["name"])
                                    if "topic" in channel_data:
                                        await channel.edit(topic=channel_data["topic"])
                                except Exception:
                                    # If forum creation fails, create a regular text channel instead
                                    channel = await category.create_text_channel(channel_data["name"])
                                    if "topic" in channel_data:
                                        await channel.edit(topic=channel_data["topic"])
                            elif channel_type == "stage" and "COMMUNITY" in interaction.guild.features:
                                try:
                                    channel = await category.create_voice_channel(channel_data["name"])
                                except Exception:
                                    # If stage creation fails, create a regular voice channel instead
                                    channel = await category.create_voice_channel(channel_data["name"])
                            else:
                                # Default to text channel for unsupported types
                                channel = await category.create_text_channel(channel_data["name"])
                                if "topic" in channel_data:
                                    await channel.edit(topic=channel_data["topic"])
                            
                            # Apply permissions if specified (only for supported channel types)
                            if "permissions" in channel_data and channel_data["permissions"] and hasattr(channel, "set_permissions"):
                                for role_name, perms in channel_data["permissions"].items():
                                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                                    if role:
                                        try:
                                            await channel.set_permissions(role, **perms)
                                        except Exception:
                                            # Skip if permission setting fails
                                            pass
                        except Exception as e:
                            # If a channel creation fails, log it but continue with other channels
                            await interaction.followup.send(f"Warning: Could not create channel {channel_data['name']}: {str(e)}", ephemeral=True)
                
                # Create roles
                created_roles = {}
                for role_data in server_structure["roles"]:
                    color = discord.Color.from_rgb(*role_data["color"])
                    role = await interaction.guild.create_role(
                        name=role_data["name"],
                        color=color,
                        hoist=role_data["displayed_separately"],
                        mentionable=role_data["mentionable"]
                    )
                    created_roles[role_data["name"]] = role
                    
                    # Set permissions if specified
                    if "permissions" in role_data and role_data["permissions"]:
                        permissions = discord.Permissions()
                        for perm_name, value in role_data["permissions"].items():
                            if hasattr(permissions, perm_name):
                                setattr(permissions, perm_name, value)
                        await role.edit(permissions=permissions)
                
                # Create information category with rules and welcome channels
                rules_category = discord.utils.get(interaction.guild.categories, name="INFORMATION")
                if not rules_category:
                    rules_category = await interaction.guild.create_category("📌 INFORMATION")
                
                # Create rules channel with content
                rules_channel = await rules_category.create_text_channel("📜-rules")
                rules_content = "# Server Rules\n\n" + "\n\n".join([f"## {i+1}. {rule}" for i, rule in enumerate(server_structure["rules"])])
                await rules_channel.send(rules_content)
                
                # Create welcome channel with welcome message
                welcome_channel = await rules_category.create_text_channel("👋-welcome")
                embed = discord.Embed(
                    title=f"Welcome to {interaction.guild.name}!",
                    description=server_structure["welcome_message"],
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
                await welcome_channel.send(embed=embed)
                
                # Create announcements channel
                try:
                    announcements_channel = await rules_category.create_text_channel("📢-announcements")
                    await announcements_channel.edit(sync_permissions=True)
                except Exception:
                    # If sync_permissions fails, just create the channel
                    announcements_channel = await rules_category.create_text_channel("📢-announcements")
                
                # Create self-roles channel if focus includes it
                if "self_roles" in self.view.focus_areas:
                    try:
                        roles_channel = await rules_category.create_text_channel("🏷️-roles")
                        await roles_channel.send("# Self Roles\n\nReact to messages below to get roles!")
                    except Exception:
                        # If there's an error, just create the channel without the message
                        await rules_category.create_text_channel("🏷️-roles")
                
                # Final success message
                # Calculate statistics
                total_channels = sum(len(c['channels']) for c in server_structure['categories']) + 3  # +3 for rules, welcome, announcements
                if "self_roles" in self.view.focus_areas:
                    total_channels += 1
                
                summary_embed = discord.Embed(
                    title="✅ Server Built Successfully!",
                    description=f"Your {self.view.server_type} server has been created with {len(server_structure['categories'])} categories and {total_channels} channels!",
                    color=discord.Color.green()
                )
                
                # Add category field with emojis
                categories_text = "\n".join([f"• {category['name']}" for category in server_structure["categories"]])
                categories_text = f"• 📌 INFORMATION\n{categories_text}"
                summary_embed.add_field(
                    name="Categories Created",
                    value=categories_text,
                    inline=False
                )
                
                # Add roles field
                summary_embed.add_field(
                    name="Roles Created",
                    value="\n".join([f"• {role['name']}" for role in server_structure["roles"]]),
                    inline=False
                )
                
                # Add recommended bots field if present
                if "recommended_bots" in server_structure:
                    summary_embed.add_field(
                        name="Recommended Bots",
                        value="\n".join([f"• {bot}" for bot in server_structure["recommended_bots"]]),
                        inline=False
                    )
                
                # Add custom input acknowledgment if provided
                if interaction.user.id in server_builder.pending_custom_inputs:
                    summary_embed.add_field(
                        name="Custom Input Applied",
                        value="Your custom description and feature requests were incorporated into the server design.",
                        inline=False
                    )
                    # Clear the custom input after use
                    del server_builder.pending_custom_inputs[interaction.user.id]
                
                await interaction.followup.send(embed=summary_embed)
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error building server: {str(e)}")
            
            # Disable all controls after building
            for child in self.view.children:
                child.disabled = True
            
            await interaction.edit_original_response(view=self.view)
    
    class ServerBuilderView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=300)  # 5 minute timeout
            
            self.cog = cog
            self.server_type = None
            self.member_scale = None
            self.moderation_level = None
            self.focus_areas = []
            
            # Add all the components
            self.add_item(ServerBuilder.ServerTypeSelect())
            self.add_item(ServerBuilder.MemberScaleSelect())
            self.add_item(ServerBuilder.ModerationSelect())
            self.add_item(ServerBuilder.FocusAreasSelect())
            self.add_item(ServerBuilder.CustomInputButton())
            self.add_item(ServerBuilder.BuildServerButton())
            
            # Initially disable all except the first dropdown
            self.children[1].disabled = True
            self.children[2].disabled = True
            self.children[3].disabled = True
            self.children[4].disabled = True
            self.children[5].disabled = True
    
    @app_commands.command(
        name="server-builder",
        description="Build a complete Discord server with AI-generated structure"
    )
    @app_commands.default_permissions(administrator=True)
    async def server_builder_command(self, interaction: discord.Interaction):
        """Build a complete Discord server with AI-generated structure"""
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ You need Administrator permission to use this command.",
                ephemeral=True
            )
        
        # Create and send the view
        view = self.ServerBuilderView(self)
        await interaction.response.send_message(
            "# 🏗️ AI Server Builder\n\nLet's build your perfect Discord server! Follow these steps to create your customized server.\n\nStart by selecting a server type:",
            view=view
        )

async def setup(bot):
    await bot.add_cog(ServerBuilder(bot))
