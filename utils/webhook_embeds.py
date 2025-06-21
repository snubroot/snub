import discord
import datetime

def create_ticket_webhook_embed(interaction, channel, ticket_number, ticket_id, issue):
    """Create a stylish embed for new ticket creation webhook notification"""
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

def claim_ticket_webhook_embed(interaction, channel_mention, ticket_id, ticket, issue_text):
    """Create a stylish embed for ticket claim webhook notification"""
    webhook_embed = discord.Embed(
        title="👤 Ticket Claimed",
        description=f"Ticket #{ticket_id.split('-')[1]} has been claimed by {interaction.user.mention}.",
        color=0x9b59b6,  # Purple color
        timestamp=datetime.datetime.now()
    )
    
    # Get the user who created the ticket
    user_mention = f"<@{ticket['user_id']}>"
    
    # Add ticket information fields
    webhook_embed.add_field(
        name="Ticket",
        value=f"{channel_mention} (#{ticket_id.split('-')[1]})",
        inline=True
    )
    webhook_embed.add_field(
        name="Claimed by",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=True
    )
    webhook_embed.add_field(
        name="User",
        value=user_mention,
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

def delete_ticket_webhook_embed(interaction, ticket_id, ticket, issue_text):
    """Create a stylish embed for ticket deletion webhook notification"""
    webhook_embed = discord.Embed(
        title="🗑️ Ticket Deleted",
        description=f"Ticket #{ticket_id.split('-')[1]} has been deleted by {interaction.user.mention}.",
        color=0xe74c3c,  # Red color
        timestamp=datetime.datetime.now()
    )
    
    # Get the user who created the ticket
    user_mention = f"<@{ticket['user_id']}>"
    
    # Add ticket information fields
    webhook_embed.add_field(
        name="Ticket",
        value=f"#{ticket_id.split('-')[1]}",
        inline=True
    )
    webhook_embed.add_field(
        name="Deleted by",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=True
    )
    webhook_embed.add_field(
        name="User",
        value=user_mention,
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

def close_ticket_webhook_embed(interaction, channel, ticket_id, ticket, issue_text):
    """Create a stylish embed for ticket closing webhook notification"""
    webhook_embed = discord.Embed(
        title="🔒 Ticket Closed",
        description=f"Ticket #{ticket_id.split('-')[1]} has been closed by {interaction.user.mention}.",
        color=0xf39c12,  # Orange color
        timestamp=datetime.datetime.now()
    )
    
    # Get the user who created the ticket
    user_mention = f"<@{ticket['user_id']}>"
    
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
        value=user_mention,
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

def reopen_ticket_webhook_embed(interaction, channel, ticket_id, ticket, issue_text):
    """Create a stylish embed for ticket reopening webhook notification"""
    webhook_embed = discord.Embed(
        title="🔓 Ticket Reopened",
        description=f"Ticket #{ticket_id.split('-')[1]} has been reopened by {interaction.user.mention}.",
        color=0x2ecc71,  # Green color
        timestamp=datetime.datetime.now()
    )
    
    # Get the user who created the ticket
    user_mention = f"<@{ticket['user_id']}>"
    
    # Add ticket information fields
    webhook_embed.add_field(
        name="Ticket",
        value=f"{channel.mention} (#{ticket_id.split('-')[1]})",
        inline=True
    )
    webhook_embed.add_field(
        name="Reopened by",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=True
    )
    webhook_embed.add_field(
        name="User",
        value=user_mention,
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
