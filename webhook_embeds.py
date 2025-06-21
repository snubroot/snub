"""
This is a temporary file with the webhook embed code for reference.
"""

import discord
import datetime

# For ticket creation
def create_ticket_webhook_embed(interaction, channel, ticket_number, ticket_id, issue):
    # Create a stylish embed for the webhook
    webhook_embed = discord.Embed(
        title="🎫 New Ticket Created",
        description=f"A new support ticket has been created by {interaction.user.mention}.",
        color=0x3498db,  # Nice blue color
        timestamp=datetime.datetime.now()
    )
    
    # Add ticket information fields
    webhook_embed.add_field(
        name="User",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=True
    )
    webhook_embed.add_field(
        name="Ticket",
        value=f"{channel.mention} (#{ticket_number})",
        inline=True
    )
    webhook_embed.add_field(
        name="Issue",
        value=issue[:1024] if len(issue) <= 1024 else f"{issue[:1021]}...",  # Discord embed field limit
        inline=False
    )
    
    # Add footer with ticket ID
    webhook_embed.set_footer(text=f"Ticket ID: {ticket_id}")
    
    # Add user avatar if available
    if interaction.user.avatar:
        webhook_embed.set_thumbnail(url=interaction.user.avatar.url)
    
    return webhook_embed

# For ticket closing
def close_ticket_webhook_embed(interaction, channel, ticket_id, ticket, issue_text):
    # Get the user who created the ticket
    ticket_user = interaction.guild.get_member(int(ticket['user_id']))
    user_mention = f"<@{ticket['user_id']}>"
    user_name = "Unknown User"
    if ticket_user:
        user_mention = ticket_user.mention
        user_name = str(ticket_user)
    
    # Create a stylish embed for the closed ticket
    webhook_embed = discord.Embed(
        title="🔒 Ticket Closed",
        description=f"Ticket #{ticket_id.split('-')[1]} has been closed by {interaction.user.mention}.",
        color=0xf39c12,  # Orange color
        timestamp=datetime.datetime.now()
    )
    
    # Add ticket information fields
    webhook_embed.add_field(
        name="Ticket",
        value=f"{channel.mention} (#{ticket_id.split('-')[1]})",
        inline=True
    )
    webhook_embed.add_field(
        name="Closed by",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=True
    )
    webhook_embed.add_field(
        name="User",
        value=f"{user_mention} ({user_name})",
        inline=True
    )
    webhook_embed.add_field(
        name="Issue",
        value=issue_text,
        inline=False
    )
    
    # Add footer with ticket ID
    webhook_embed.set_footer(text=f"Ticket ID: {ticket_id}")
    
    # Add user avatar if available
    if interaction.user.avatar:
        webhook_embed.set_thumbnail(url=interaction.user.avatar.url)
        
    return webhook_embed

# For ticket system setup
def setup_tickets_webhook_embed(interaction):
    # Create a stylish embed for the setup notification
    webhook_embed = discord.Embed(
        title="✅ Ticket System Setup",
        description=f"The ticket system has been successfully set up by {interaction.user.mention}.",
        color=0x2ecc71,  # Green color
        timestamp=datetime.datetime.now()
    )
    
    webhook_embed.add_field(
        name="Channel",
        value=interaction.channel.mention,
        inline=True
    )
    webhook_embed.add_field(
        name="Setup by",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=True
    )
    
    # Add server icon if available
    if interaction.guild.icon:
        webhook_embed.set_thumbnail(url=interaction.guild.icon.url)
        
    return webhook_embed
