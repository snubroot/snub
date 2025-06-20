import discord
from discord.ext import commands
import traceback
import sys
import datetime
import config

class ErrorLogger(commands.Cog):
    """Logs errors to a specified Discord channel"""
    
    def __init__(self, bot):
        self.bot = bot
        self.error_channel_id = config.ERROR_LOG_CHANNEL
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors and log them to the specified channel"""
        # Get original error if it's wrapped in CommandInvokeError
        error = getattr(error, 'original', error)
        
        # Ignore some errors that shouldn't be logged
        if isinstance(error, (commands.CommandNotFound, commands.DisabledCommand)):
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
            return
            
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Bad argument: {str(error)}")
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"❌ You don't have permission to use this command.")
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"❌ I don't have the necessary permissions to do that.")
            return
            
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱️ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        
        # Log all other errors to the error channel
        await self.log_error(ctx, error)
        
        # Also inform the user that an error occurred
        try:
            await ctx.send("❌ An error occurred while executing this command. The error has been logged.")
        except discord.HTTPException:
            pass
    
    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """Handle non-command errors"""
        error_type, error, error_traceback = sys.exc_info()
        await self.log_error_event(event, error_type, error, error_traceback)
    
    async def log_error(self, ctx, error):
        """Log a command error to the error channel"""
        if not self.error_channel_id:
            print("Error logging channel not set. Set ERROR_LOG_CHANNEL in .env")
            return
            
        error_channel = self.bot.get_channel(self.error_channel_id)
        if not error_channel:
            print(f"Could not find error logging channel with ID {self.error_channel_id}")
            return
            
        # Create error embed
        embed = discord.Embed(
            title="Command Error",
            description=f"An error occurred while executing a command.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        # Add command info
        embed.add_field(
            name="Command",
            value=f"`{ctx.command.qualified_name}`" if ctx.command else "Unknown",
            inline=True
        )
        
        # Add user info
        embed.add_field(
            name="User",
            value=f"{ctx.author} (ID: {ctx.author.id})",
            inline=True
        )
        
        # Add guild info
        embed.add_field(
            name="Guild",
            value=f"{ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "DM",
            inline=True
        )
        
        # Add channel info
        embed.add_field(
            name="Channel",
            value=f"{ctx.channel} (ID: {ctx.channel.id})",
            inline=True
        )
        
        # Add message content
        embed.add_field(
            name="Message",
            value=f"```{ctx.message.content[:1000]}```",
            inline=False
        )
        
        # Add error info
        embed.add_field(
            name="Error",
            value=f"```py\n{type(error).__name__}: {str(error)[:1000]}```",
            inline=False
        )
        
        # Add traceback (limited to 1000 characters)
        traceback_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(traceback_text) > 1000:
            traceback_text = traceback_text[:997] + "..."
            
        embed.add_field(
            name="Traceback",
            value=f"```py\n{traceback_text}```",
            inline=False
        )
        
        # Set footer
        embed.set_footer(text=f"Error logged at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Send the error embed
        await error_channel.send(embed=embed)
    
    async def log_error_event(self, event_name, error_type, error, error_traceback):
        """Log a non-command error to the error channel"""
        if not self.error_channel_id:
            print("Error logging channel not set. Set ERROR_LOG_CHANNEL in .env")
            return
            
        error_channel = self.bot.get_channel(self.error_channel_id)
        if not error_channel:
            print(f"Could not find error logging channel with ID {self.error_channel_id}")
            return
            
        # Create error embed
        embed = discord.Embed(
            title="Event Error",
            description=f"An error occurred in event `{event_name}`.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        # Add error info
        embed.add_field(
            name="Error Type",
            value=f"`{error_type.__name__}`",
            inline=True
        )
        
        embed.add_field(
            name="Error Message",
            value=f"```{str(error)[:1000]}```",
            inline=False
        )
        
        # Add traceback (limited to 1000 characters)
        traceback_text = "".join(traceback.format_exception(error_type, error, error_traceback))
        if len(traceback_text) > 1000:
            traceback_text = traceback_text[:997] + "..."
            
        embed.add_field(
            name="Traceback",
            value=f"```py\n{traceback_text}```",
            inline=False
        )
        
        # Set footer
        embed.set_footer(text=f"Error logged at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Send the error embed
        await error_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ErrorLogger(bot))
