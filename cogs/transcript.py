import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import io
import asyncio
from typing import Optional, Literal
import html
import re

class Transcript(commands.Cog):
    """Generate clean, downloadable logs (TXT/HTML/PDF) of a channel for moderation, archive, or audits."""
    
    def __init__(self, bot):
        self.bot = bot
        self.max_messages = 5000  # Default maximum messages to fetch
        
    @commands.hybrid_command(name="transcript", description="Generate a transcript of messages from a channel")
    @app_commands.describe(
        channel="The channel to generate a transcript from. Defaults to current channel if not specified.",
        limit="Number of messages to include (max 5000) or days to look back",
        format="Format of the transcript (txt, html, pdf)"
    )
    async def transcript(
        self, 
        ctx: commands.Context, 
        channel: Optional[discord.TextChannel] = None,
        limit: Optional[int] = 100,
        format: Optional[Literal["txt", "html", "pdf"]] = "txt"
    ):
        """
        Generate a transcript of messages from a channel.
        
        Examples:
        !transcript here 100
        !transcript #general 7
        """
        # Defer the response since this might take a while
        await ctx.defer(ephemeral=False)
        
        # Default to the current channel if none is specified
        target_channel = channel or ctx.channel
        
        # Check permissions
        if not target_channel.permissions_for(ctx.author).read_messages:
            return await ctx.send("You don't have permission to read messages in that channel.", ephemeral=True)
        
        if not target_channel.permissions_for(ctx.guild.me).read_message_history:
            return await ctx.send("I don't have permission to read message history in that channel.", ephemeral=True)
        
        # Limit the number of messages
        if limit > self.max_messages:
            limit = self.max_messages
            await ctx.send(f"Limiting transcript to {self.max_messages} messages.", ephemeral=True)
        
        # Fetch messages
        try:
            messages = []
            async for message in target_channel.history(limit=limit):
                messages.append(message)
            
            # Reverse to get chronological order
            messages.reverse()
            
            if not messages:
                return await ctx.send("No messages found in the specified channel.", ephemeral=True)
            
            # Generate transcript based on format
            if format == "txt":
                file = await self.generate_txt_transcript(messages, target_channel)
            elif format == "html":
                file = await self.generate_html_transcript(messages, target_channel)
            elif format == "pdf":
                # For PDF, we'll generate HTML first and note that a conversion would be needed
                file = await self.generate_html_transcript(messages, target_channel, for_pdf=True)
                await ctx.send("Note: PDF conversion would require additional libraries. Providing HTML format instead.")
            
            # Send the transcript file
            await ctx.send(
                f"📄 Transcript for {target_channel.mention} ({len(messages)} messages)",
                file=file
            )
            
        except Exception as e:
            await ctx.send(f"An error occurred while generating the transcript: {str(e)}", ephemeral=True)
    
    @commands.hybrid_command(name="transcript_dm", description="Generate a transcript of DM messages with a user")
    @app_commands.describe(
        user="The user to generate a DM transcript with",
        limit="Number of messages to include (max 5000)",
        format="Format of the transcript (txt, html, pdf)"
    )
    async def transcript_dm(
        self, 
        ctx: commands.Context, 
        user: discord.User,
        limit: Optional[int] = 100,
        format: Optional[Literal["txt", "html", "pdf"]] = "txt"
    ):
        """
        Generate a transcript of DM messages with a user.
        
        Example:
        !transcript dm @user
        """
        # This command should only work in DMs
        if ctx.guild is not None:
            return await ctx.send("This command can only be used in DMs for privacy reasons. Please use it in a DM with me.", ephemeral=True)
        
        # Defer the response since this might take a while
        await ctx.defer(ephemeral=True)
        
        # Get the DM channel with the user
        dm_channel = user.dm_channel
        if dm_channel is None:
            try:
                dm_channel = await user.create_dm()
            except discord.HTTPException:
                return await ctx.send("I couldn't create a DM channel with that user.", ephemeral=True)
        
        # Limit the number of messages
        if limit > self.max_messages:
            limit = self.max_messages
            await ctx.send(f"Limiting transcript to {self.max_messages} messages.", ephemeral=True)
        
        # Fetch messages
        try:
            messages = []
            async for message in dm_channel.history(limit=limit):
                messages.append(message)
            
            # Reverse to get chronological order
            messages.reverse()
            
            if not messages:
                return await ctx.send("No messages found in the DM channel.", ephemeral=True)
            
            # Generate transcript based on format
            if format == "txt":
                file = await self.generate_txt_transcript(messages, dm_channel)
            elif format == "html":
                file = await self.generate_html_transcript(messages, dm_channel)
            elif format == "pdf":
                # For PDF, we'll generate HTML first and note that a conversion would be needed
                file = await self.generate_html_transcript(messages, dm_channel, for_pdf=True)
                await ctx.send("Note: PDF conversion would require additional libraries. Providing HTML format instead.")
            
            # Send the transcript file
            await ctx.send(
                f"📄 DM Transcript with {user.name} ({len(messages)} messages)",
                file=file,
                ephemeral=True
            )
            
        except Exception as e:
            await ctx.send(f"An error occurred while generating the transcript: {str(e)}", ephemeral=True)
    
    async def generate_txt_transcript(self, messages, channel):
        """Generate a plain text transcript from messages"""
        transcript_text = f"Transcript of {channel.name if hasattr(channel, 'name') else 'DM Channel'}\n"
        transcript_text += f"Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        transcript_text += f"Total Messages: {len(messages)}\n\n"
        transcript_text += "-" * 80 + "\n\n"
        
        for message in messages:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author_name = message.author.name
            content = message.content or "[No text content]"
            
            transcript_text += f"[{timestamp}] {author_name}: {content}\n"
            
            # Add attachments
            for attachment in message.attachments:
                transcript_text += f"[Attachment: {attachment.filename} - {attachment.url}]\n"
            
            # Add embeds
            if message.embeds:
                transcript_text += f"[Message contains {len(message.embeds)} embed(s)]\n"
            
            transcript_text += "\n"
        
        # Create file object
        file_obj = io.BytesIO(transcript_text.encode('utf-8'))
        
        # Create the discord File
        channel_name = channel.name if hasattr(channel, 'name') else "dm_transcript"
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{channel_name}_transcript_{date_str}.txt"
        
        return discord.File(file_obj, filename=filename)
    
    async def generate_html_transcript(self, messages, channel, for_pdf=False):
        """Generate an HTML transcript from messages"""
        guild_name = getattr(channel.guild, 'name', 'Direct Messages')
        channel_name = getattr(channel, 'name', 'DM Channel')
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript - {channel_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            background-color: #5865F2;
            color: white;
            padding: 15px;
            border-radius: 5px 5px 0 0;
            margin-bottom: 20px;
        }}
        .message {{
            padding: 10px;
            margin-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .message:hover {{
            background-color: #f9f9f9;
        }}
        .message-info {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .author {{
            font-weight: bold;
            margin-right: 10px;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.8em;
        }}
        .content {{
            margin-left: 50px;
            word-wrap: break-word;
        }}
        .attachment {{
            margin-top: 5px;
            margin-left: 50px;
        }}
        .attachment a {{
            color: #5865F2;
            text-decoration: none;
        }}
        .attachment a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            color: #999;
            font-size: 0.8em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Transcript - {html.escape(channel_name)}</h1>
        <p>Server: {html.escape(guild_name)}</p>
        <p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p>Total Messages: {len(messages)}</p>
    </div>
    <div class="messages">
"""
        
        for message in messages:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author_name = html.escape(message.author.name)
            avatar_url = message.author.display_avatar.url
            
            # Process message content (escape HTML and convert URLs to links)
            content = html.escape(message.content or "[No text content]")
            # Convert URLs to clickable links
            url_pattern = r'(https?://[^\s]+)'
            content = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', content)
            # Convert newlines to <br>
            content = content.replace('\n', '<br>')
            
            html_content += f"""
    <div class="message">
        <div class="message-info">
            <img class="avatar" src="{avatar_url}" alt="{author_name}'s avatar">
            <span class="author">{author_name}</span>
            <span class="timestamp">{timestamp}</span>
        </div>
        <div class="content">{content}</div>
"""
            
            # Add attachments
            for attachment in message.attachments:
                html_content += f"""
        <div class="attachment">
            <a href="{attachment.url}" target="_blank">[Attachment: {html.escape(attachment.filename)}]</a>
        </div>
"""
            
            # Add embeds
            if message.embeds:
                html_content += f"""
        <div class="attachment">
            [Message contains {len(message.embeds)} embed(s)]
        </div>
"""
            
            html_content += """
    </div>
"""
        
        # Close the HTML
        html_content += """
    </div>
    <div class="footer">
        <p>Generated by Snub Discord Bot</p>
    </div>
</body>
</html>
"""
        
        # Create file object
        file_obj = io.BytesIO(html_content.encode('utf-8'))
        
        # Create the discord File
        channel_name = channel.name if hasattr(channel, 'name') else "dm_transcript"
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{channel_name}_transcript_{date_str}.html"
        
        return discord.File(file_obj, filename=filename)

async def setup(bot):
    await bot.add_cog(Transcript(bot))
