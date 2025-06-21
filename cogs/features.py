import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Optional, List

class Features(commands.Cog):
    """Display all features and commands of the Snub Discord bot in organized embeds."""
    
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.blue()
        self.thumbnail_url = "https://i.imgur.com/your_thumbnail.png"  # Replace with actual thumbnail URL
        
    @commands.hybrid_command(
        name="features",
        description="Display all features and commands of the Snub Discord bot"
    )
    @app_commands.describe(
        category="Optional category to display specific features"
    )
    async def features(self, ctx, category: Optional[str] = None):
        """
        Display all features and commands of the Snub Discord bot.
        
        Parameters:
        - category: Optional category to display specific features
        """
        if category:
            await self.show_category(ctx, category.lower())
        else:
            await self.show_main_menu(ctx)
    
    async def show_main_menu(self, ctx):
        """Show the main menu with all feature categories."""
        embed = discord.Embed(
            title="🤖 Snub Discord Bot Features",
            description="A powerful, modular Discord bot with various features and commands.\n"
                       "Select a category below to see detailed commands.",
            color=self.color
        )
        
        # Add fields for each category
        embed.add_field(
            name="🛠️ Core Features",
            value="• Modular Design\n• Dynamic Cog Management\n• Error Logging\n• Beautiful Embeds",
            inline=True
        )
        
        embed.add_field(
            name="👥 User Management",
            value="• Reaction Roles\n• Verification System\n• Ticket System\n• Birthday Tracking",
            inline=True
        )
        
        embed.add_field(
            name="🧠 AI Features",
            value="• OpenAI Integration\n• AI Server Builder\n• Dream Journal\n• DeepAI Integration",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Server Management",
            value="• Sticky Messages\n• Welcome Messages\n• Invite Tracking",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Fun & Utility",
            value="• Would You Rather\n• Dad Jokes\n• Fortune Cookies\n• Reddit Memes",
            inline=True
        )
        
        embed.add_field(
            name="📊 Information",
            value="• Number Facts\n• Wikipedia Integration\n• News\n• Currency & Crypto",
            inline=True
        )
        
        embed.add_field(
            name="💬 Mental Health",
            value="• Mental Health Check-In\n• Mood Tracking\n• Journaling Prompts",
            inline=False
        )
        
        embed.add_field(
            name="📝 Transcripts",
            value="• Channel Transcripts\n• DM Transcripts",
            inline=True
        )
        
        # Add footer with usage instructions
        embed.set_footer(text="Use !features <category> to see specific commands (e.g., !features ai)")
        
        # Send the embed
        message = await ctx.send(embed=embed)
        
        # Add reactions for navigation
        reactions = ["🛠️", "👥", "🧠", "⚙️", "🎮", "📊", "💬", "📝"]
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        # Wait for reaction response
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            # Map reactions to categories
            category_map = {
                "🛠️": "core",
                "👥": "user",
                "🧠": "ai",
                "⚙️": "server",
                "🎮": "fun",
                "📊": "info",
                "💬": "mental",
                "📝": "transcripts"
            }
            
            await message.delete()
            await self.show_category(ctx, category_map[str(reaction.emoji)])
            
        except asyncio.TimeoutError:
            await message.clear_reactions()
    
    async def show_category(self, ctx, category):
        """Show commands for a specific category."""
        if category == "core":
            await self.show_core_features(ctx)
        elif category == "user":
            await self.show_user_management(ctx)
        elif category == "ai":
            await self.show_ai_features(ctx)
        elif category == "server":
            await self.show_server_management(ctx)
        elif category == "fun":
            await self.show_fun_features(ctx)
        elif category == "info":
            await self.show_info_features(ctx)
        elif category == "mental":
            await self.show_mental_health(ctx)
        elif category == "transcripts":
            await self.show_transcripts(ctx)
        else:
            await ctx.send(f"Category '{category}' not found. Use `!features` to see all categories.")

    async def show_core_features(self, ctx):
        """Display core features and commands."""
        embed = discord.Embed(
            title="🛠️ Core Features",
            description="Essential features and commands that power the Snub Discord bot.",
            color=self.color
        )
        
        # Cog Management
        embed.add_field(
            name="🧩 Cog Management",
            value=(
                "```bash\n"
                "!cogs - List all available cogs and their status\n"
                "!cog load <n> - Load a specific cog\n"
                "!cog unload <n> - Unload a specific cog\n"
                "!cog refresh <n> - Refresh a cog\n"
                "```"
            ),
            inline=False
        )
        
        # Sync Commands
        embed.add_field(
            name="🔄 Sync Commands",
            value=(
                "```bash\n"
                "!sync - Sync slash commands with Discord\n"
                "```"
            ),
            inline=False
        )
        
        # Ping Command
        embed.add_field(
            name="📶 Ping Command",
            value=(
                "```bash\n"
                "!ping - Check the bot's latency\n"
                "/ping - Check the bot's latency (slash command)\n"
                "```"
            ),
            inline=False
        )
        
        # Help Command
        embed.add_field(
            name="❓ Help Command",
            value=(
                "```bash\n"
                "!help - Show help for all commands\n"
                "!help <command> - Show help for a specific command\n"
                "```"
            ),
            inline=False
        )
        
        # Error Logging
        embed.add_field(
            name="🔍 Error Logging",
            value="Comprehensive error tracking with Discord channel logging. Errors are automatically logged to the configured error log channel.",
            inline=False
        )
        
        embed.set_footer(text="Use !features to return to the main menu")
        await ctx.send(embed=embed)
    
    async def show_user_management(self, ctx):
        """Display user management features and commands."""
        embed = discord.Embed(
            title="👥 User Management",
            description="Features for managing users, roles, and permissions.",
            color=self.color
        )
        
        # Reaction Roles
        embed.add_field(
            name="🎭 Reaction Roles",
            value=(
                "```bash\n"
                "/reactionrole-add <category> <role> <emoji> - Add a role to a category\n"
                "/reactionrole-button <category> [channel] - Create a button panel\n"
                "/reactionrole-menu <category> [channel] - Create a dropdown menu panel\n"
                "/reactionrole-list - List all categories\n"
                "/reactionrole-delete <category> - Delete a category\n"
                "```"
            ),
            inline=False
        )
        
        # Verification System
        embed.add_field(
            name="🔐 Verification System",
            value=(
                "```bash\n"
                "!enableverify - Enable the verification system\n"
                "!disableverify - Disable the verification system\n"
                "!setverify <channel_id> - Set the channel for verification\n"
                "!setverifyrole <@role> - Set the role to assign upon verification\n"
                "```"
            ),
            inline=False
        )
        
        # Ticket System
        embed.add_field(
            name="🎫 Ticket System",
            value=(
                "```bash\n"
                "/ticket <issue> - Create a new support ticket\n"
                "/tickets - View all active tickets\n"
                "/setup-tickets - Set up the ticket system\n"
                "```"
            ),
            inline=False
        )
        
        # Birthday Tracking
        embed.add_field(
            name="🎂 Birthday Tracking",
            value=(
                "```bash\n"
                "!birthday set <month> <day> - Set your birthday\n"
                "!birthday remove - Remove your birthday\n"
                "!birthday list - List upcoming birthdays\n"
                "!birthday next - Show the next upcoming birthday\n"
                "!birthday today - Check if anyone has a birthday today\n"
                "!birthday channel <#channel> - Set birthday announcement channel\n"
                "```"
            ),
            inline=False
        )
        
        # Family System
        embed.add_field(
            name="👪 Family System",
            value="Create virtual families with adoption, marriage, and family relationship management.",
            inline=False
        )
        
        # Invite Tracking
        embed.add_field(
            name="📨 Invite Tracking",
            value="Track who invited whom with detailed statistics and leaderboards.",
            inline=False
        )
        
        embed.set_footer(text="Use !features to return to the main menu")
        await ctx.send(embed=embed)
        
    async def show_ai_features(self, ctx):
        pass
        
    async def show_server_management(self, ctx):
        pass
        
    async def show_fun_features(self, ctx):
        pass
        
    async def show_info_features(self, ctx):
        pass
        
    async def show_mental_health(self, ctx):
        pass
        
    async def show_transcripts(self, ctx):
        pass

async def setup(bot):
    await bot.add_cog(Features(bot))
