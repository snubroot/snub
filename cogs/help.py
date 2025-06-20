import discord
from discord.ext import commands
import datetime
from typing import Dict, List, Optional, Union


class HelpCommand(commands.Cog):
    """Custom help command with beautiful embeds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x3498db  # A nice blue color
        
        bot.remove_command("help")
    
    def get_command_signature(self, command):
        """Get the command signature with proper formatting"""
        if isinstance(command, commands.Group):
            return f"`{command.qualified_name} <subcommand>`"
        
        params = []
        for param in command.clean_params.values():
            if param.default == param.empty:
                params.append(f"<{param.name}>")
            else:
                params.append(f"[{param.name}]")
        
        if params:
            return f"`{command.qualified_name} {' '.join(params)}`"
        else:
            return f"`{command.qualified_name}`"
    
    def get_category_emoji(self, category: str) -> str:
        """Get an appropriate emoji for a category"""
        category = category.lower()
        emoji_map = {
            "general": "📊",
            "moderation": "🛡️",
            "admin": "⚙️",
            "ticket": "🎫",
            "tickets": "🎫",
            "reaction": "🎭",
            "reactionrole": "🎭",
            "sticky": "📌",
            "stickymessage": "📌",
            "cog": "🧩",
            "help": "❓",
            "utility": "🔧",
            "fun": "🎮",
            "music": "🎵",
            "ping": "🏓",
            "misc": "📦",
            "numbers": "🔢",
            "number": "🔢"
        }
        
        for key, emoji in emoji_map.items():
            if key in category:
                return emoji
        
        return "🔹"
        
    def get_app_command_signature(self, command):
        """Get the signature for an application command (slash command)"""
        params = []
        for param in command.parameters:
            if param.required:
                params.append(f"<{param.name}>")
            else:
                params.append(f"[{param.name}]")
        
        if params:
            return f"`/{command.name} {' '.join(params)}`"
        else:
            return f"`/{command.name}`"
    
    def get_app_commands_by_cog(self):
        """Group app commands by cog"""
        # Create a direct mapping based on command name prefixes
        command_categories = {
            # Numbers category
            "number": "Numbers",
            "math_fact": "Numbers",
            "date_fact": "Numbers",
            "year_fact": "Numbers",
            "random_number_fact": "Numbers",
            "number_trivia": "Numbers",
            
            # Reaction Roles category
            "reactionrole": "Reaction Roles",
            
            # Tickets category
            "ticket": "Tickets",
            "setup-tickets": "Tickets",
            "_ticket": "Tickets",
            
            # Utility category
            "ping": "Utility",
            "help": "Utility",
            "sync": "Utility",
            
            # Fun category
            "wouldurather": "Fun",
            
            # Family category
            "family": "Family",
            
            # Birthdays category
            "birthday": "Birthdays",
            
            # Sticky Messages category
            "sticky": "Sticky Messages",
            
            # Invites category
            "invite": "Invites",
            
            # OpenAI category
            "ai": "OpenAI",
            "gpt": "OpenAI",
            "openai": "OpenAI",
        }
        
        # Initialize category mapping
        cog_mapping = {
            "Numbers": [],
            "Reaction Roles": [],
            "Tickets": [],
            "Utility": [],
            "Fun": [],
            "Family": [],
            "Birthdays": [],
            "Sticky Messages": [],
            "Invites": [],
            "OpenAI": [],
            "No Category": []
        }
        
        # Map commands to categories based on their names
        for command in self.bot.tree.get_commands():
            found = False
            command_name = command.name.lower()
            
            # Try to match command to a category based on prefixes
            for prefix, category in command_categories.items():
                if command_name.startswith(prefix.lower()):
                    cog_mapping[category].append(command)
                    found = True
                    break
            
            # If no match found, check if it's a reactionrole command (special case)
            if not found and "reactionrole" in command_name:
                cog_mapping["Reaction Roles"].append(command)
                found = True
            
            # If still no match, put in No Category
            if not found:
                cog_mapping["No Category"].append(command)
        
        # Remove empty categories
        return {k: v for k, v in cog_mapping.items() if v}
    
    def create_help_embed(self, title: str, description: str) -> discord.Embed:
        """Create a beautiful embed for help commands"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=self.color,
            timestamp=datetime.datetime.now()
        )
        
        embed.set_author(
            name=f"{self.bot.user.name} Help",
            icon_url=self.bot.user.display_avatar.url
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.description += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        embed.set_footer(
            text=f"Type !help <command> for more info on a command",
            icon_url=self.bot.user.display_avatar.url
        )
        
        return embed
    
    @commands.command(name="help")
    async def help_command(self, ctx, *, command_name: str = None):
        """Shows help for a command or lists all commands"""
        if command_name is None:
            await self.send_bot_help(ctx)
        else:
            await self.send_command_help(ctx, command_name)
    
    async def send_bot_help(self, ctx):
        """Send the main help page with all command categories"""
        cog_mapping: Dict[str, List[commands.Command]] = {}
        
        for command in self.bot.commands:
            if command.hidden:
                continue
                
            cog_name = command.cog.qualified_name if command.cog else "No Category"
            
            if cog_name not in cog_mapping:
                cog_mapping[cog_name] = []
                
            cog_mapping[cog_name].append(command)
        
        app_command_mapping = self.get_app_commands_by_cog()
        
        for cog_name, app_commands_list in app_command_mapping.items():
            if cog_name not in cog_mapping:
                cog_mapping[cog_name] = []
        
        bot_name = self.bot.user.name
        embed = self.create_help_embed(
            f"📚 {bot_name} Help Menu",
            f"Welcome to the **{bot_name}** help system! Below you'll find all available commands grouped by category.\n\n"
            f"**🔹 Usage Tips:**\n"
            f"• Use `!help <command>` for detailed command info\n"
            f"• Use `!help <category>` to see all commands in a category\n"
            f"• Use `!help slash` to see all slash commands\n"
        )
        
        total_prefix_commands = sum(len(cmds) for cmds in cog_mapping.values())
        total_app_commands = sum(len(cmds) for cmds in app_command_mapping.values())
        total_categories = len(cog_mapping)
        
        embed.add_field(
            name="📊 Bot Statistics",
            value=f"• **{total_prefix_commands}** commands available\n"
                  f"• **{total_app_commands}** slash commands available\n"
                  f"• **{total_categories}** command categories\n"
                  f"• **{len(self.bot.guilds)}** servers connected",
            inline=False
        )
        
        for cog_name, commands_list in sorted(cog_mapping.items()):
            if not commands_list and cog_name not in app_command_mapping:
                continue
                
            cog = self.bot.get_cog(cog_name)
            description = cog.description if cog and cog.description else "No description"
            
            emoji = self.get_category_emoji(cog_name)
            
            command_list = []
            for cmd in sorted(commands_list, key=lambda x: x.name):
                command_list.append(f"`{cmd.name}`")
            
            formatted_commands = ", ".join(command_list)
            
            has_slash = cog_name in app_command_mapping and len(app_command_mapping[cog_name]) > 0
            slash_indicator = " + 🔍" if has_slash else ""
            
            embed.add_field(
                name=f"{emoji} {cog_name} ({len(commands_list)}{slash_indicator})",
                value=f"*{description}*\n{formatted_commands}",
                inline=False
            )
        
        total_slash = sum(len(cmds) for cmds in app_command_mapping.values())
        if total_slash > 0:
            embed.add_field(
                name="🔍 Slash Commands",
                value=f"This bot has **{total_slash}** slash commands. Type `/` in Discord to see them or use `!help slash` for details.",
                inline=False
            )
        
        embed.add_field(
            name="💡 Tip",
            value="Commands marked with 🔒 require special permissions to use.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def send_command_help(self, ctx, command_name: str):
        """Send help for a specific command or category"""
        if command_name.lower() == "slash":
            await self.send_slash_commands_help(ctx)
            return
            
        for cog_name, cog in self.bot.cogs.items():
            if command_name.lower() == cog_name.lower():
                await self.send_cog_help(ctx, cog)
                return
        
        command = self.bot.get_command(command_name)
        if command is None:
            embed = self.create_help_embed(
                "❌ Command Not Found",
                f"No command called `{command_name}` was found.\n\nUse `!help` to see all available commands."
            )
            return await ctx.send(embed=embed)
        
        cog_name = command.cog.qualified_name if command.cog else "No Category"
        emoji = self.get_category_emoji(cog_name)
        
        embed = self.create_help_embed(
            f"{emoji} Command: {command.name}",
            command.help or "No description available."
        )
        
        embed.add_field(
            name="📝 Usage",
            value=self.get_command_signature(command),
            inline=False
        )
        
        embed.add_field(
            name="📂 Category",
            value=f"`{cog_name}`",
            inline=True
        )
        
        required_perms = "Everyone"
        if hasattr(command.callback, "__commands_checks__"):
            for check in command.callback.__commands_checks__:
                if "is_owner" in str(check):
                    required_perms = "🔒 Bot Owner"
                elif "has_permissions" in str(check) or "has_guild_permissions" in str(check):
                    required_perms = "🔒 Special Permissions"
        
        embed.add_field(
            name="🔑 Permissions",
            value=required_perms,
            inline=True
        )
        
        if command.aliases:
            embed.add_field(
                name="🔄 Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False
            )
        
        example = f"`{command.name}`"
        if command.clean_params:
            example = f"`{command.name} [arguments]`"
        
        embed.add_field(
            name="💡 Example",
            value=example,
            inline=False
        )
        
        if isinstance(command, commands.Group):
            subcommands = [f"`{c.name}` - {c.short_doc or 'No description'}" for c in command.commands]
            if subcommands:
                embed.add_field(
                    name="📋 Subcommands",
                    value="\n".join(subcommands),
                    inline=False
                )
        
        related_commands = []
        if command.cog:
            for cmd in command.cog.get_commands():
                if cmd != command and not cmd.hidden:
                    related_commands.append(f"`{cmd.name}`")
        
        if related_commands:
            embed.add_field(
                name="🔗 Related Commands",
                value=", ".join(related_commands[:5]) + ("..." if len(related_commands) > 5 else ""),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    async def send_slash_commands_help(self, ctx):
        """Send help for all slash commands"""
        app_command_mapping = self.get_app_commands_by_cog()
        
        if not app_command_mapping:
            embed = self.create_help_embed(
                "🔍 Slash Commands",
                "No slash commands are available."
            )
            return await ctx.send(embed=embed)
        
        # Create the main embed
        main_embed = self.create_help_embed(
            "🔍 Slash Commands",
            "Use the dropdown menu below to view slash commands by category."
        )
        
        total_slash = sum(len(cmds) for cmds in app_command_mapping.values())
        
        main_embed.add_field(
            name="📊 Statistics",
            value=f"**{total_slash}** slash commands available across **{len(app_command_mapping)}** categories",
            inline=False
        )
        
        main_embed.add_field(
            name="💡 Tip",
            value="Use `/` in Discord to see these commands in the Discord interface.",
            inline=False
        )
        
        # Create a simple dropdown menu for categories
        class CategorySelect(discord.ui.Select):
            def __init__(self, help_command, app_command_mapping):
                self.help_command = help_command
                self.app_command_mapping = app_command_mapping
                
                # Create options for the dropdown
                options = []
                for cog_name, commands_list in sorted(app_command_mapping.items()):
                    if not commands_list:
                        continue
                        
                    emoji = help_command.get_category_emoji(cog_name)
                    options.append(
                        discord.SelectOption(
                            label=f"{cog_name} ({len(commands_list)})",
                            description=f"View {len(commands_list)} slash commands",
                            value=cog_name,
                            emoji=emoji
                        )
                    )
                
                # Add an "Overview" option
                options.insert(0, discord.SelectOption(
                    label="Overview",
                    description="Return to the main overview",
                    value="overview",
                    emoji="🏠"
                ))
                
                super().__init__(
                    placeholder="Select a category...",
                    min_values=1,
                    max_values=1,
                    options=options
                )
            
            async def callback(self, interaction):
                selected_value = self.values[0]
                
                if selected_value == "overview":
                    await interaction.response.edit_message(embed=main_embed)
                    return
                
                # Get the commands for the selected category
                commands_list = self.app_command_mapping.get(selected_value, [])
                if not commands_list:
                    await interaction.response.send_message("No commands found for this category.", ephemeral=True)
                    return
                
                # Create an embed for the selected category
                cog_name = selected_value
                cog = None
                
                # Find the actual cog object
                for c in self.help_command.bot.cogs.values():
                    if c.__class__.__name__.endswith('Cog') and c.__class__.__name__[:-3] == cog_name:
                        cog = c
                        break
                    elif c.__class__.__name__ == cog_name:
                        cog = c
                        break
                
                description = cog.description if cog else "No description available"
                emoji = self.help_command.get_category_emoji(cog_name)
                
                category_embed = self.help_command.create_help_embed(
                    f"{emoji} {cog_name} Slash Commands",
                    f"*{description}*\n\nHere are all the slash commands in this category:"
                )
                
                # Sort and format commands
                sorted_commands = sorted(commands_list, key=lambda x: x.name)
                command_texts = []
                
                for cmd in sorted_commands:
                    requires_perms = ""
                    if hasattr(cmd, "default_permissions") and cmd.default_permissions:
                        requires_perms = " 🔒"
                    
                    command_texts.append(f"{self.help_command.get_app_command_signature(cmd)}{requires_perms} - {cmd.description or '*No description*'}")
                
                # Split commands into chunks to avoid Discord's 1024 character limit
                chunks = []
                current_chunk = []
                current_length = 0
                
                for cmd_text in command_texts:
                    if current_length + len(cmd_text) + 1 > 1000:  # Using 1000 to be safe
                        chunks.append(current_chunk)
                        current_chunk = [cmd_text]
                        current_length = len(cmd_text)
                    else:
                        current_chunk.append(cmd_text)
                        current_length += len(cmd_text) + 1
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Add fields for each chunk
                if not chunks:
                    category_embed.add_field(
                        name="No Commands",
                        value="There are no slash commands in this category.",
                        inline=False
                    )
                else:
                    for i, chunk in enumerate(chunks):
                        field_name = f"Commands" if i == 0 else f"Commands (continued {i})"
                        category_embed.add_field(
                            name=field_name,
                            value="\n".join(chunk),
                            inline=False
                        )
                
                await interaction.response.edit_message(embed=category_embed)
        
        class HelpView(discord.ui.View):
            def __init__(self, help_command, app_command_mapping):
                super().__init__(timeout=300)  # 5 minute timeout
                self.add_item(CategorySelect(help_command, app_command_mapping))
        
        # Create and send the view
        view = HelpView(self, app_command_mapping)
        await ctx.send(embed=main_embed, view=view)
    
    async def send_cog_help(self, ctx, cog):
        """Send help for a specific cog/category"""
        commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
        app_command_mapping = self.get_app_commands_by_cog()
        app_commands_list = app_command_mapping.get(cog.qualified_name, [])
        
        if not commands_list and not app_commands_list:
            embed = self.create_help_embed(
                f"Category: {cog.qualified_name}",
                "This category has no commands."
            )
            return await ctx.send(embed=embed)
        
        emoji = self.get_category_emoji(cog.qualified_name)
        embed = self.create_help_embed(
            f"{emoji} {cog.qualified_name} Category",
            cog.description or "No description available."
        )
        
        embed.add_field(
            name="📊 Category Stats",
            value=f"**{len(commands_list)}** prefix commands and **{len(app_commands_list)}** slash commands available in this category",
            inline=False
        )
        
        commands_list.sort(key=lambda x: x.name)
        
        if commands_list:
            embed.add_field(
                name="⌨️ Prefix Commands",
                value="The following commands can be used with the bot's prefix:",
                inline=False
            )
            
            for command in commands_list:
                requires_perms = ""
                if hasattr(command.callback, "__commands_checks__"):
                    for check in command.callback.__commands_checks__:
                        if "is_owner" in str(check) or "has_permissions" in str(check):
                            requires_perms = " 🔒"
                
                signature = self.get_command_signature(command)
                
                embed.add_field(
                    name=f"{signature}{requires_perms}",
                    value=command.short_doc or "*No description available.*",
                    inline=False
                )
        
        if app_commands_list:
            embed.add_field(
                name="🔍 Slash Commands",
                value="The following slash commands are available in this category:",
                inline=False
            )
            
            for command in sorted(app_commands_list, key=lambda x: x.name):
                requires_perms = ""
                if hasattr(command, "default_permissions") and command.default_permissions:
                    requires_perms = " 🔒"
                
                signature = self.get_app_command_signature(command)
                
                embed.add_field(
                    name=f"{signature}{requires_perms}",
                    value=command.description or "*No description available.*",
                    inline=False
                )
        
        embed.add_field(
            name="💡 Tip",
            value=f"Type `!help <command>` for more details on a specific command.",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
