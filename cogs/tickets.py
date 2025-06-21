import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import asyncio
import json
import os
import aiohttp
from dotenv import load_dotenv
from utils import webhook_embeds

class TicketModal(ui.Modal, title="Create a Support Ticket"):
    issue = ui.TextInput(
        label="What do you need help with?",
        placeholder="Please describe your issue...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        
    async def on_submit(self, interaction: discord.Interaction):
        # Instead of calling the slash command directly, call a separate method
        await self.cog.process_ticket_modal(interaction, str(self.issue))

load_dotenv()

TICKET_DATA_FILE = "data/tickets.json"

TICKET_WEBHOOK = os.getenv('TICKET_WEBHOOK')

class Tickets(commands.Cog):
    """Ticket system for creating and managing support channels. This module allows users to create private support tickets, which staff can claim, close, and manage. Features include ticket creation, tracking, notifications, and a complete workflow for handling user support requests."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ticket_data = {}
        self._load_ticket_data()
        
        if not hasattr(self.bot, 'session'):
            self.bot.session = aiohttp.ClientSession()
        
        command = app_commands.Command(
            name="_ticket_buttons",
            description="Hidden command for ticket buttons",
            callback=self._dummy_command
        )
        command.guild_only = True
        bot.tree.add_command(command)
        
        self.bot.add_listener(self.on_interaction, "on_interaction")
        
    async def _dummy_command(self, interaction: discord.Interaction):
        """Dummy command for button handlers"""
        pass
        
    async def process_ticket_modal(self, interaction: discord.Interaction, issue: str):
        """Process a ticket creation from the modal"""
        try:
            user_id = str(interaction.user.id)
            for ticket_id, ticket in self.ticket_data["active_tickets"].items():
                if ticket["user_id"] == user_id:
                    await interaction.response.send_message(
                        "You already have an open ticket! Please use that one instead.",
                        ephemeral=True
                    )
                    return
            
            self.ticket_data["ticket_counter"] += 1
            ticket_number = self.ticket_data["ticket_counter"]
            ticket_id = f"ticket-{ticket_number}"
            
            guild = interaction.guild
            category = None
            
            for c in guild.categories:
                if c.name.lower() == "tickets":
                    category = c
                    break
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            channel = await guild.create_text_channel(
                name=f"ticket-{ticket_number}",
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user.name} | Issue: {issue[:50]}"
            )
            
            self.ticket_data["active_tickets"][ticket_id] = {
                "user_id": user_id,
                "channel_id": channel.id,
                "issue": issue,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "open"
            }
            self._save_ticket_data()
            
            # Send initial response to the user
            await interaction.response.send_message(f"Ticket created! Check {channel.mention}", ephemeral=True)
            
            # Send webhook notification if configured
            if TICKET_WEBHOOK:
                try:
                    webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                    issue_text = issue[:1000] if len(issue) > 1000 else issue
                    webhook_embed = webhook_embeds.create_ticket_webhook_embed(interaction, channel, ticket_number, ticket_id, issue_text)
                    await webhook.send(embed=webhook_embed)
                except Exception as webhook_error:
                    print(f"Error sending webhook notification: {webhook_error}")
            
            # Create and send the ticket embed in the new channel
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_number} Created",
                description=f"Thank you for creating a ticket. Support staff will be with you shortly.",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Issue", value=issue, inline=False)
            embed.add_field(name="Created By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Status", value="📝 Open", inline=True)
            
            embed.set_footer(text=f"Ticket ID: {ticket_id}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            close_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id=f"close_ticket:{ticket_id}")
            claim_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Claim Ticket", custom_id=f"claim_ticket:{ticket_id}")
            
            view = discord.ui.View()
            view.add_item(close_button)
            view.add_item(claim_button)
            
            await channel.send(f"{interaction.user.mention} Support staff will be with you shortly.", embed=embed, view=view)
            
        except Exception as e:
            print(f"Error creating ticket from modal: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred while creating your ticket: {e}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"An error occurred while creating your ticket: {e}",
                    ephemeral=True
                )
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions"""
        if not interaction.data or not interaction.data.get("custom_id"):
            return
            
        custom_id = interaction.data.get("custom_id")
        
        if custom_id.startswith("close_ticket:"):
            await self.close_ticket(interaction, custom_id.split(":")[1])
        elif custom_id.startswith("claim_ticket:"):
            await self.claim_ticket(interaction, custom_id.split(":")[1])
        elif custom_id.startswith("delete_ticket:"):
            await self.delete_ticket(interaction, custom_id.split(":")[1])
        elif custom_id.startswith("reopen_ticket:"):
            await self.reopen_ticket(interaction, custom_id.split(":")[1])
        elif custom_id == "create_ticket":
            modal = TicketModal(self)
            await interaction.response.send_modal(modal)
        
    @app_commands.command(name="ticket", description="Create a new support ticket")
    @app_commands.describe(issue="Briefly describe your issue")
    async def create_ticket(self, interaction: discord.Interaction, issue: str):
        """Create a new support ticket"""
        try:
            user_id = str(interaction.user.id)
            for ticket_id, ticket in self.ticket_data["active_tickets"].items():
                if ticket["user_id"] == user_id:
                    await interaction.response.send_message(
                        "You already have an open ticket! Please use that one instead.",
                        ephemeral=True
                    )
                    return
            
            self.ticket_data["ticket_counter"] += 1
            ticket_number = self.ticket_data["ticket_counter"]
            ticket_id = f"ticket-{ticket_number}"
            
            guild = interaction.guild
            category = None
            
            for c in guild.categories:
                if c.name.lower() == "tickets":
                    category = c
                    break
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            channel = await guild.create_text_channel(
                name=f"ticket-{ticket_number}",
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user.name} | Issue: {issue[:50]}"
            )
            
            self.ticket_data["active_tickets"][ticket_id] = {
                "user_id": user_id,
                "channel_id": channel.id,
                "issue": issue,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "open"
            }
            self._save_ticket_data()
            
            # Send initial response to the user
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Ticket created! Check {channel.mention}", ephemeral=True)
            else:
                await interaction.followup.send(f"Ticket created! Check {channel.mention}", ephemeral=True)
            
            # Send webhook notification if configured
            if TICKET_WEBHOOK:
                try:
                    webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                    issue_text = issue[:1000] if len(issue) > 1000 else issue
                    webhook_embed = webhook_embeds.create_ticket_webhook_embed(interaction, channel, ticket_number, ticket_id, issue_text)
                    await webhook.send(embed=webhook_embed)
                except Exception as webhook_error:
                    print(f"Error sending webhook notification: {webhook_error}")
        
            # Create and send the ticket embed in the new channel
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_number} Created",
                description=f"Thank you for creating a ticket. Support staff will be with you shortly.",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Issue", value=issue, inline=False)
            embed.add_field(name="Created By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Status", value="📝 Open", inline=True)
            
            embed.set_footer(text=f"Ticket ID: {ticket_id}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            close_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id=f"close_ticket:{ticket_id}")
            claim_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Claim Ticket", custom_id=f"claim_ticket:{ticket_id}")
            
            view = discord.ui.View()
            view.add_item(close_button)
            view.add_item(claim_button)
            
            await channel.send(f"{interaction.user.mention} Support staff will be with you shortly.", embed=embed, view=view)
            
        except Exception as e:
            print(f"Error creating ticket: {e}")
            await interaction.response.send_message(
                f"An error occurred while creating your ticket: {e}",
                ephemeral=True
            )
        
    def _load_ticket_data(self):
        """Load ticket data from file"""
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(TICKET_DATA_FILE):
                with open(TICKET_DATA_FILE, "r") as f:
                    self.ticket_data = json.load(f)
            else:
                self.ticket_data = {"ticket_counter": 0, "active_tickets": {}, "closed_tickets": {}}
                self._save_ticket_data()
        except Exception as e:
            print(f"Error loading ticket data: {e}")
            self.ticket_data = {"ticket_counter": 0, "active_tickets": {}, "closed_tickets": {}}
    
    def _save_ticket_data(self):
        """Save ticket data to file"""
        try:
            with open(TICKET_DATA_FILE, "w") as f:
                json.dump(self.ticket_data, f, indent=4)
        except Exception as e:
            print(f"Error saving ticket data: {e}")
            
    async def close_ticket(self, interaction: discord.Interaction, ticket_id: str):
        """Close a ticket"""
        try:
            if ticket_id not in self.ticket_data["active_tickets"]:
                await interaction.response.send_message("This ticket no longer exists.", ephemeral=True)
                return
                
            ticket = self.ticket_data["active_tickets"][ticket_id]
            channel_id = ticket["channel_id"]
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message("The ticket channel no longer exists.", ephemeral=True)
                return
                
            ticket["status"] = "closed"
            ticket["closed_by"] = interaction.user.id
            ticket["closed_at"] = datetime.datetime.now().isoformat()
            
            self.ticket_data["closed_tickets"][ticket_id] = ticket
            del self.ticket_data["active_tickets"][ticket_id]
            self._save_ticket_data()
            
            embed = discord.Embed(
                title=f"🔒 Ticket #{ticket_id.split('-')[1]} Closed",
                description=f"This ticket has been closed by {interaction.user.mention}.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Original Issue", value=ticket["issue"], inline=False)
            embed.add_field(name="Status", value="🔒 Closed", inline=True)
            embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
            
            embed.set_footer(text=f"Ticket ID: {ticket_id}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            delete_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Delete Ticket", custom_id=f"delete_ticket:{ticket_id}")
            reopen_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Reopen Ticket", custom_id=f"reopen_ticket:{ticket_id}")
            
            view = discord.ui.View()
            view.add_item(delete_button)
            view.add_item(reopen_button)
            
            ticket_creator = interaction.guild.get_member(int(ticket["user_id"]))
            if ticket_creator:
                await channel.set_permissions(ticket_creator, send_messages=False)
            
            await interaction.response.send_message(embed=embed, view=view)
            
            if TICKET_WEBHOOK:
                try:
                    webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                    issue_text = ticket['issue'][:500] + "..." if len(ticket['issue']) > 500 else ticket['issue']
                    
                    # Get the user who created the ticket
                    ticket_user = interaction.guild.get_member(int(ticket['user_id']))
                    user_mention = f"<@{ticket['user_id']}>"
                    user_name = "Unknown User"
                    if ticket_creator:
                        user_name = str(ticket_creator)
                    
                    webhook_embed = webhook_embeds.close_ticket_webhook_embed(interaction, channel, ticket_id, ticket, issue_text)
                    await webhook.send(embed=webhook_embed)
                except Exception as webhook_error:
                    print(f"Error sending webhook notification: {webhook_error}")
        
        except Exception as e:
            print(f"Error closing ticket: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            
    async def claim_ticket(self, interaction: discord.Interaction, ticket_id: str):
        """Claim a ticket"""
        try:
            if ticket_id not in self.ticket_data["active_tickets"]:
                await interaction.response.send_message("This ticket no longer exists.", ephemeral=True)
                return
                
            ticket = self.ticket_data["active_tickets"][ticket_id]
            
            ticket["claimed_by"] = interaction.user.id
            ticket["claimed_at"] = datetime.datetime.now().isoformat()
            self._save_ticket_data()
            
            embed = discord.Embed(
                title=f"👤 Ticket #{ticket_id.split('-')[1]} Claimed",
                description=f"This ticket has been claimed by {interaction.user.mention}.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Original Issue", value=ticket["issue"], inline=False)
            embed.add_field(name="Status", value="👤 Claimed", inline=True)
            embed.add_field(name="Staff Member", value=interaction.user.mention, inline=True)
            
            embed.set_footer(text=f"Ticket ID: {ticket_id}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await interaction.response.send_message(embed=embed)
            
            if TICKET_WEBHOOK:
                try:
                    webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                    channel_id = ticket["channel_id"]
                    channel = interaction.guild.get_channel(channel_id)
                    channel_mention = channel.mention if channel else f"#deleted-channel"
                    issue_text = ticket['issue'][:500] + "..." if len(ticket['issue']) > 500 else ticket['issue']
                    
                    webhook_embed = webhook_embeds.claim_ticket_webhook_embed(interaction, channel_mention, ticket_id, ticket, issue_text)
                    await webhook.send(embed=webhook_embed)
                except Exception as webhook_error:
                    print(f"Error sending webhook notification: {webhook_error}")
            
        except Exception as e:
            print(f"Error claiming ticket: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            
    async def delete_ticket(self, interaction: discord.Interaction, ticket_id: str):
        """Delete a ticket"""
        try:
            if ticket_id not in self.ticket_data["closed_tickets"]:
                await interaction.response.send_message("This ticket no longer exists or is not closed.", ephemeral=True)
                return
                
            ticket = self.ticket_data["closed_tickets"][ticket_id]
            channel_id = ticket["channel_id"]
            channel = interaction.guild.get_channel(channel_id)
            
            embed = discord.Embed(
                title=f"🗑️ Ticket #{ticket_id.split('-')[1]} Deleted",
                description=f"This ticket is being deleted by {interaction.user.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            await interaction.response.send_message(embed=embed)
            
            if TICKET_WEBHOOK:
                try:
                    webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                    issue_text = ticket['issue'][:500] + "..." if len(ticket['issue']) > 500 else ticket['issue']
                    webhook_embed = webhook_embeds.delete_ticket_webhook_embed(interaction, ticket_id, ticket, issue_text)
                    await webhook.send(embed=webhook_embed)
                except Exception as webhook_error:
                    print(f"Error sending webhook notification: {webhook_error}")
            
            del self.ticket_data["closed_tickets"][ticket_id]
            self._save_ticket_data()
            
            if channel:
                await asyncio.sleep(5)
                await channel.delete(reason=f"Ticket {ticket_id} deleted by {interaction.user}")
            
        except Exception as e:
            print(f"Error deleting ticket: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            
    async def reopen_ticket(self, interaction: discord.Interaction, ticket_id: str):
        """Reopen a closed ticket"""
        try:
            if ticket_id not in self.ticket_data["closed_tickets"]:
                await interaction.response.send_message("This ticket no longer exists or is not closed.", ephemeral=True)
                return
                
            ticket = self.ticket_data["closed_tickets"][ticket_id]
            channel_id = ticket["channel_id"]
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message("The ticket channel no longer exists.", ephemeral=True)
                return
                
            ticket["status"] = "open"
            ticket["reopened_by"] = interaction.user.id
            ticket["reopened_at"] = datetime.datetime.now().isoformat()
            
            self.ticket_data["active_tickets"][ticket_id] = ticket
            del self.ticket_data["closed_tickets"][ticket_id]
            self._save_ticket_data()
            
            embed = discord.Embed(
                title=f"🔓 Ticket #{ticket_id.split('-')[1]} Reopened",
                description=f"This ticket has been reopened by {interaction.user.mention}.",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Original Issue", value=ticket["issue"], inline=False)
            embed.add_field(name="Status", value="🔓 Reopened", inline=True)
            embed.add_field(name="Reopened By", value=interaction.user.mention, inline=True)
            
            embed.set_footer(text=f"Ticket ID: {ticket_id}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            close_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id=f"close_ticket:{ticket_id}")
            claim_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Claim Ticket", custom_id=f"claim_ticket:{ticket_id}")
            
            view = discord.ui.View()
            view.add_item(close_button)
            view.add_item(claim_button)
            
            ticket_creator = interaction.guild.get_member(int(ticket["user_id"]))
            if ticket_creator:
                await channel.set_permissions(ticket_creator, send_messages=True)
            
            await interaction.response.send_message(embed=embed, view=view)
            
            if TICKET_WEBHOOK:
                try:
                    webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                    issue_text = ticket['issue'][:500] + "..." if len(ticket['issue']) > 500 else ticket['issue']
                    webhook_embed = webhook_embeds.reopen_ticket_webhook_embed(interaction, channel, ticket_id, ticket, issue_text)
                    await webhook.send(embed=webhook_embed)
                except Exception as webhook_error:
                    print(f"Error sending webhook notification: {webhook_error}")
            
        except Exception as e:
            print(f"Error reopening ticket: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="tickets", description="View all active tickets")
    @app_commands.default_permissions(administrator=True)
    async def list_tickets(self, interaction: discord.Interaction):
        """List all active tickets"""
        try:
            if not self.ticket_data["active_tickets"]:
                await interaction.response.send_message("There are no active tickets.", ephemeral=True)
                return
                
            embed = discord.Embed(
                title=f"📜 Active Tickets",
                description=f"There are currently **{len(self.ticket_data['active_tickets'])}** active tickets.",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            for ticket_id, ticket in self.ticket_data["active_tickets"].items():
                ticket_number = ticket_id.split('-')[1]
                channel = interaction.guild.get_channel(ticket["channel_id"])
                user = interaction.guild.get_member(int(ticket["user_id"]))
                
                status = "📝 Open"
                if "claimed_by" in ticket:
                    status = "👤 Claimed"
                    
                channel_mention = "Channel deleted"
                if channel:
                    channel_mention = channel.mention
                    
                user_mention = "User left"
                if user:
                    user_mention = user.mention
                    
                value = f"**User:** {user_mention}\n**Channel:** {channel_mention}\n**Status:** {status}\n**Created:** <t:{int(datetime.datetime.fromisoformat(ticket['created_at']).timestamp())}:R>"
                
                embed.add_field(name=f"Ticket #{ticket_number}", value=value, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error listing tickets: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="setup-tickets", description="Set up the ticket system")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        """Set up the ticket system"""
        try:
            # First check if webhook is configured
            if not TICKET_WEBHOOK:
                await interaction.response.send_message(
                    "⚠️ Ticket webhook is not configured. Please add a TICKET_WEBHOOK to your .env file.", 
                    ephemeral=True
                )
                return
            
            # Defer the response immediately to prevent interaction timeout
            await interaction.response.defer(ephemeral=True)
                
            try:
                webhook = discord.Webhook.from_url(TICKET_WEBHOOK, session=self.bot.session)
                test_embed = discord.Embed(
                    title="🔄 Webhook Test",
                    description="Setting up ticket system - testing webhook connection",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now()
                )
                test_msg = await webhook.send(embed=test_embed, wait=True)
                await test_msg.delete()
            except discord.NotFound:
                await interaction.followup.send(
                    "⚠️ The configured webhook URL is invalid or the webhook has been deleted. Please update your TICKET_WEBHOOK in the .env file.",
                    ephemeral=True
                )
                return
            except Exception as webhook_error:
                await interaction.followup.send(
                    f"⚠️ Error validating webhook: {webhook_error}. Please check your TICKET_WEBHOOK configuration.",
                    ephemeral=True
                )
                return
                
            # Check for existing tickets category
            category = None
            for c in interaction.guild.categories:
                if c.name.lower() == "tickets":
                    category = c
                    break
                    
            # Create category if needed
            category_created = False
            if not category:
                category = await interaction.guild.create_category("Tickets")
                category_created = True
            
            # Create the embed for ticket creation
            embed = discord.Embed(
                title="🎫 Support Tickets",
                description="Need help? Click the button below to create a support ticket.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="How it works",
                value="1. Click the button below\n2. Enter a brief description of your issue\n3. A private channel will be created for you",
                inline=False
            )
            
            embed.set_footer(text=f"Support Ticket System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            # Create the ticket button
            create_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Create Ticket", emoji="🎫", custom_id="create_ticket")
            
            view = discord.ui.View()
            view.add_item(create_button)
            
            # Send the ticket creation message
            ticket_msg = await interaction.channel.send(embed=embed, view=view)
            
            # Send status message to webhook
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
                
            await webhook.send(embed=webhook_embed)
            
            # Send final response to user
            response_text = "✅ Ticket system has been set up successfully!"
            if category_created:
                response_text += f"\n• Created category {category.name}"
            response_text += f"\n• Created ticket message with button"
            
            await interaction.followup.send(response_text, ephemeral=True)
            
        except Exception as e:
            print(f"Error setting up tickets: {e}")
            try:
                # Try to send followup if we've already deferred
                await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
            except:
                # If that fails, try to send a response
                try:
                    await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
                except:
                    # If all else fails, just print to console
                    print(f"Could not send error message to user: {e}")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
