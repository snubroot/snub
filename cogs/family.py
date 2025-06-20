import discord
from discord.ext import commands
import json
import os
from typing import Dict, List, Optional, Union
import datetime
import asyncio

class Family(commands.Cog):
    """Virtual family relationship system for Discord servers. This module allows users to create family connections with other server members through marriage, adoption, and parental relationships. Features include proposing to partners, adopting children, viewing family trees, and managing family relationships with interactive confirmation buttons."""
    def __init__(self, bot):
        self.bot = bot
        self.family_data = {}
        self.family_file = "data/family.json"
        self.load_data()
        
    def load_data(self):
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(self.family_file):
                with open(self.family_file, "r") as f:
                    self.family_data = json.load(f)
        except Exception as e:
            print(f"Error loading family data: {e}")
            self.family_data = {}
            
    def save_data(self):
        try:
            with open(self.family_file, "w") as f:
                json.dump(self.family_data, f, indent=4)
        except Exception as e:
            print(f"Error saving family data: {e}")
    
    def get_user_family(self, guild_id: str, user_id: str):
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        if guild_id not in self.family_data:
            self.family_data[guild_id] = {}
            
        if user_id not in self.family_data[guild_id]:
            self.family_data[guild_id][user_id] = {
                "Partner": None,
                "Parent": [],
                "Children": []
            }
            
        return self.family_data[guild_id][user_id]

    @commands.command(name="family")
    async def family(self, ctx, user: discord.Member = None):
        """View your or someone else's family"""
        target = user or ctx.author
        
        family_data = self.get_user_family(ctx.guild.id, target.id)
        
        embed = discord.Embed(
            title=f"👪 {target.display_name}'s Family",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Partner field
        partner_value = "This user is not married"
        if family_data["Partner"]:
            try:
                partner = await self.bot.fetch_user(int(family_data["Partner"]))
                partner_value = f"{partner.mention}"
            except:
                partner_value = "Unknown user"
        
        embed.add_field(
            name="Partner",
            value=partner_value,
            inline=False
        )
        
        # Parents field
        parents_value = "This user has no parents"
        if family_data["Parent"] and len(family_data["Parent"]) > 0:
            parents = []
            for parent_id in family_data["Parent"]:
                try:
                    parent = await self.bot.fetch_user(int(parent_id))
                    parents.append(parent.mention)
                except:
                    pass
            
            if parents:
                parents_value = ", ".join(parents)
        
        embed.add_field(
            name="Parents",
            value=parents_value,
            inline=False
        )
        
        # Children field
        children_value = "This user has no children"
        if family_data["Children"] and len(family_data["Children"]) > 0:
            children = []
            for child_id in family_data["Children"]:
                try:
                    child = await self.bot.fetch_user(int(child_id))
                    children.append(child.mention)
                except:
                    pass
            
            if children:
                children_value = ", ".join(children)
        
        embed.add_field(
            name="Children",
            value=children_value,
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)

    @commands.command(name="adopt")
    async def adopt(self, ctx, user: discord.Member):
        """Adopt a user as your child"""
        author = ctx.author
        
        if author.id == user.id:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot adopt yourself",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if user.bot:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot adopt a bot",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Check if they are already family members
        author_data = self.get_user_family(ctx.guild.id, author.id)
        target_data = self.get_user_family(ctx.guild.id, user.id)
        
        # Check if target is already a parent of the author
        if str(user.id) in author_data["Parent"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot adopt a family member!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Check if author is already a parent of the target
        if str(author.id) in target_data["Parent"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You are already a parent of this user!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Check if they are partners
        if target_data["Partner"] == str(author.id) or author_data["Partner"] == str(user.id):
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot adopt your partner!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Check if target already has parents
        if target_data["Parent"] and len(target_data["Parent"]) > 0:
            embed = discord.Embed(
                title="❌ Error",
                description="This user already has parents!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Create adoption request embed
        embed = discord.Embed(
            title="👪 Adoption Request",
            description=f"{author.mention} wants to adopt {user.mention}!\n{user.mention}, do you accept?",
            color=discord.Color.blue()
        )
        
        # Create buttons for response
        yes_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Accept", custom_id="adopt_yes", emoji="✅")
        no_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Decline", custom_id="adopt_no", emoji="❌")
        
        view = discord.ui.View()
        view.add_item(yes_button)
        view.add_item(no_button)
        
        message = await ctx.send(content=user.mention, embed=embed, view=view)
        
        def check(interaction):
            return interaction.user.id == user.id and interaction.message.id == message.id
        
        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            
            if interaction.data["custom_id"] == "adopt_yes":
                # Update family data
                author_data = self.get_user_family(ctx.guild.id, author.id)
                target_data = self.get_user_family(ctx.guild.id, user.id)
                
                # Add child to author
                if str(user.id) not in author_data["Children"]:
                    author_data["Children"].append(str(user.id))
                
                # Add parent to target
                if str(author.id) not in target_data["Parent"]:
                    target_data["Parent"].append(str(author.id))
                
                self.save_data()
                
                # Success embed
                success_embed = discord.Embed(
                    title="👪 Adoption - Approved",
                    description=f"{author.mention} is now the proud parent of {user.mention}! 🎉",
                    color=discord.Color.green()
                )
                
                await interaction.response.edit_message(embed=success_embed, view=None)
                
            elif interaction.data["custom_id"] == "adopt_no":
                # Declined embed
                declined_embed = discord.Embed(
                    title="👪 Adoption - Declined",
                    description=f"{user.mention} doesn't want to be adopted by {author.mention}",
                    color=discord.Color.red()
                )
                
                await interaction.response.edit_message(embed=declined_embed, view=None)
                
        except asyncio.TimeoutError:
            # Timeout embed
            timeout_embed = discord.Embed(
                title="👪 Adoption - Cancelled",
                description=f"{user.mention} didn't respond! The adoption is cancelled",
                color=discord.Color.red()
            )
            
            await message.edit(embed=timeout_embed, view=None)

    @commands.command(name="disown")
    async def disown(self, ctx, user: discord.Member):
        """Disown one of your children"""
        author = ctx.author
        
        if author.id == user.id:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot disown yourself",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if user.bot:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot disown a bot",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        author_data = self.get_user_family(ctx.guild.id, author.id)
        target_data = self.get_user_family(ctx.guild.id, user.id)
        
        # Check if the target is a child of the author
        if str(user.id) not in author_data["Children"]:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{user.display_name} is not your child",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Remove child from author
        author_data["Children"].remove(str(user.id))
        
        # Remove parent from target
        if str(author.id) in target_data["Parent"]:
            target_data["Parent"].remove(str(author.id))
        
        self.save_data()
        
        embed = discord.Embed(
            title="👪 Disowned",
            description=f"{author.mention} has disowned {user.mention}",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="propose")
    async def propose(self, ctx, user: discord.Member):
        """Propose to another user"""
        author = ctx.author
        
        if author.id == user.id:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot marry yourself!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if user.bot:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot marry a bot!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        author_data = self.get_user_family(ctx.guild.id, author.id)
        target_data = self.get_user_family(ctx.guild.id, user.id)
        
        # Check if either is already married
        if author_data["Partner"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You are already married!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if target_data["Partner"]:
            embed = discord.Embed(
                title="❌ Error",
                description="This user is already married!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Check if they are family members
        if str(user.id) in author_data["Children"] or str(author.id) in target_data["Children"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot marry a family member!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if str(user.id) in author_data["Parent"] or str(author.id) in target_data["Parent"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot marry a family member!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Create proposal embed
        embed = discord.Embed(
            title="👰 Marriage Proposal",
            description=f"{author.mention} has proposed to {user.mention}!\n{user.mention}, do you accept?",
            color=discord.Color.pink()
        )
        
        # Create buttons for response
        yes_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Accept", custom_id="propose_yes", emoji="✅")
        no_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Decline", custom_id="propose_no", emoji="❌")
        
        view = discord.ui.View()
        view.add_item(yes_button)
        view.add_item(no_button)
        
        message = await ctx.send(content=user.mention, embed=embed, view=view)
        
        def check(interaction):
            return interaction.user.id == user.id and interaction.message.id == message.id
        
        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            
            if interaction.data["custom_id"] == "propose_yes":
                # Update family data
                author_data = self.get_user_family(ctx.guild.id, author.id)
                target_data = self.get_user_family(ctx.guild.id, user.id)
                
                # Set partners
                author_data["Partner"] = str(user.id)
                target_data["Partner"] = str(author.id)
                
                self.save_data()
                
                # Success embed
                success_embed = discord.Embed(
                    title="👰 Marriage Proposal - Accepted",
                    description=f"{author.mention} and {user.mention} are now married! 👰🎉",
                    color=discord.Color.green()
                )
                
                await interaction.response.edit_message(embed=success_embed, view=None)
                
            elif interaction.data["custom_id"] == "propose_no":
                # Declined embed
                declined_embed = discord.Embed(
                    title="👰 Marriage Proposal - Declined",
                    description=f"{user.mention} loves someone else and chose not to marry {author.mention}",
                    color=discord.Color.red()
                )
                
                await interaction.response.edit_message(embed=declined_embed, view=None)
                
        except asyncio.TimeoutError:
            # Timeout embed
            timeout_embed = discord.Embed(
                title="👰 Marriage Proposal - Cancelled",
                description=f"{user.mention} has not answered! The wedding is cancelled",
                color=discord.Color.red()
            )
            
            await message.edit(embed=timeout_embed, view=None)

    @commands.command(name="divorce")
    async def divorce(self, ctx, user: discord.Member = None):
        """Divorce your partner"""
        author = ctx.author
        
        author_data = self.get_user_family(ctx.guild.id, author.id)
        
        if not author_data["Partner"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You are not married!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # If user is specified, check if they are the partner
        if user and str(user.id) != author_data["Partner"]:
            embed = discord.Embed(
                title="❌ Error",
                description="You are not married to this user!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Get partner data
        partner_id = author_data["Partner"]
        partner_data = self.get_user_family(ctx.guild.id, partner_id)
        
        # Clear partner data
        author_data["Partner"] = None
        partner_data["Partner"] = None
        
        self.save_data()
        
        try:
            partner = await self.bot.fetch_user(int(partner_id))
            partner_mention = partner.mention
        except:
            partner_mention = "their partner"
        
        embed = discord.Embed(
            title="👰 Divorced",
            description=f"{author.mention} has divorced {partner_mention}",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="deletefamily")
    async def delete_family(self, ctx):
        """Delete your entire family record"""
        author = ctx.author
        
        # Create confirmation embed
        embed = discord.Embed(
            title="❓ Reset Family",
            description="Are you sure you want to reset your family? This action cannot be undone.",
            color=discord.Color.yellow()
        )
        
        # Create buttons for response
        yes_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Yes", custom_id="family_delete_yes", emoji="✅")
        no_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="No", custom_id="family_delete_no", emoji="❌")
        
        view = discord.ui.View()
        view.add_item(yes_button)
        view.add_item(no_button)
        
        message = await ctx.send(embed=embed, view=view)
        
        def check(interaction):
            return interaction.user.id == author.id and interaction.message.id == message.id
        
        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            
            if interaction.data["custom_id"] == "family_delete_yes":
                guild_id = str(ctx.guild.id)
                user_id = str(author.id)
                
                # Get user's family data
                if guild_id in self.family_data and user_id in self.family_data[guild_id]:
                    user_data = self.family_data[guild_id][user_id]
                    
                    # Handle partner
                    if user_data["Partner"]:
                        partner_id = user_data["Partner"]
                        if guild_id in self.family_data and partner_id in self.family_data[guild_id]:
                            partner_data = self.family_data[guild_id][partner_id]
                            partner_data["Partner"] = None
                    
                    # Handle parents
                    for parent_id in user_data["Parent"]:
                        if guild_id in self.family_data and parent_id in self.family_data[guild_id]:
                            parent_data = self.family_data[guild_id][parent_id]
                            if user_id in parent_data["Children"]:
                                parent_data["Children"].remove(user_id)
                    
                    # Handle children
                    for child_id in user_data["Children"]:
                        if guild_id in self.family_data and child_id in self.family_data[guild_id]:
                            child_data = self.family_data[guild_id][child_id]
                            if user_id in child_data["Parent"]:
                                child_data["Parent"].remove(user_id)
                    
                    # Delete user data
                    del self.family_data[guild_id][user_id]
                    self.save_data()
                
                # Success embed
                success_embed = discord.Embed(
                    title="✅ Family Reset",
                    description="Your family has been deleted!",
                    color=discord.Color.green()
                )
                
                await interaction.response.edit_message(embed=success_embed, view=None)
                
            elif interaction.data["custom_id"] == "family_delete_no":
                # Cancelled embed
                cancelled_embed = discord.Embed(
                    title="❌ Family Reset - Cancelled",
                    description="Family reset cancelled.",
                    color=discord.Color.red()
                )
                
                await interaction.response.edit_message(embed=cancelled_embed, view=None)
                
        except asyncio.TimeoutError:
            # Timeout embed
            timeout_embed = discord.Embed(
                title="❌ Family Reset - Cancelled",
                description="Family reset cancelled due to timeout.",
                color=discord.Color.red()
            )
            
            await message.edit(embed=timeout_embed, view=None)

async def setup(bot):
    await bot.add_cog(Family(bot))
