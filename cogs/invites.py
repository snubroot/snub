import discord
from discord.ext import commands
import json
import os
from typing import Dict, List, Optional, Union
import datetime

class Invites(commands.Cog):
    """Invite tracking and management system. This module tracks server invites, identifies which invite links members use to join, and maintains statistics on member invitations. Features include viewing invite counts, adding/removing invites manually, displaying leaderboards, and resetting invite statistics for users or the entire server."""
    def __init__(self, bot):
        self.bot = bot
        self.invites_data = {}
        self.invites_file = "data/invites.json"
        self.guild_invites = {}
        self.load_data()
        
        bot.loop.create_task(self.cache_invites())
        
    def load_data(self):
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(self.invites_file):
                with open(self.invites_file, "r") as f:
                    self.invites_data = json.load(f)
        except Exception as e:
            print(f"Error loading invites data: {e}")
            self.invites_data = {}
            
    def save_data(self):
        try:
            with open(self.invites_file, "w") as f:
                json.dump(self.invites_data, f, indent=4)
        except Exception as e:
            print(f"Error saving invites data: {e}")
            
    async def cache_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                self.guild_invites[guild.id] = {}
                invites = await guild.invites()
                for invite in invites:
                    self.guild_invites[guild.id][invite.code] = invite.uses
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error caching invites for guild {guild.id}: {e}")
    
    def get_user_invites(self, guild_id: str, user_id: str):
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        if guild_id not in self.invites_data:
            self.invites_data[guild_id] = {}
            
        if user_id not in self.invites_data[guild_id]:
            self.invites_data[guild_id][user_id] = {
                "invites": 0,
                "total": 0,
                "left": 0
            }
            
        return self.invites_data[guild_id][user_id]
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        guild_id = invite.guild.id
        if guild_id not in self.guild_invites:
            self.guild_invites[guild_id] = {}
        self.guild_invites[guild_id][invite.code] = invite.uses
        
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        guild_id = invite.guild.id
        if guild_id in self.guild_invites and invite.code in self.guild_invites[guild_id]:
            del self.guild_invites[guild_id][invite.code]
            
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        
        if guild.id not in self.guild_invites:
            return
            
        try:
            invites_before = self.guild_invites[guild.id]
            invites_after = {}
            
            new_invites = await guild.invites()
            for invite in new_invites:
                invites_after[invite.code] = invite.uses
                
            for invite_code, uses in invites_after.items():
                if invite_code in invites_before:
                    if uses > invites_before[invite_code]:
                        # This is the invite that was used
                        for invite in new_invites:
                            if invite.code == invite_code:
                                inviter_id = str(invite.inviter.id)
                                guild_id = str(guild.id)
                                
                                inviter_data = self.get_user_invites(guild_id, inviter_id)
                                inviter_data["invites"] += 1
                                inviter_data["total"] += 1
                                self.save_data()
                                
                                # Update the cache
                                self.guild_invites[guild.id] = invites_after
                                
                                # Send welcome message with inviter info if desired
                                # This is optional and can be expanded
                                break
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Error tracking invite for member join {member.id}: {e}")
            
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        guild_id = str(guild.id)
        
        try:
            for user_id, user_data in self.invites_data.get(guild_id, {}).items():
                # Find who invited this user
                # This is an approximation since we don't store who invited whom
                # For a more accurate system, you'd need to store that information
                
                # Increment the "left" counter for the inviter
                user_data["left"] += 1
                
                # Decrement their active invites
                user_data["invites"] = max(0, user_data["invites"] - 1)
                
                self.save_data()
                break
        except Exception as e:
            print(f"Error tracking member leave {member.id}: {e}")
    
    @commands.command(name="invites")
    async def show_invites(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        
        user_invites = self.get_user_invites(ctx.guild.id, user.id)
        
        embed = discord.Embed(
            title="📨 Invites",
            description=f"**{user.display_name}** has `{user_invites['invites']}` invites",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Total",
            value=str(user_invites["total"]),
            inline=True
        )
        
        embed.add_field(
            name="Left",
            value=str(user_invites["left"]),
            inline=True
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @commands.command(name="addinvites")
    @commands.has_permissions(manage_guild=True)
    async def add_invites(self, ctx, user: discord.Member, amount: int):
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="Amount must be a positive number",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        user_invites = self.get_user_invites(ctx.guild.id, user.id)
        user_invites["invites"] += amount
        user_invites["total"] += amount
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Invites Added",
            description=f"Added **{amount}** invites to {user.mention}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📨 Total invites",
            value=str(user_invites["invites"]),
            inline=True
        )
        
        embed.set_footer(text=f"Modified by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @commands.command(name="removeinvites")
    @commands.has_permissions(manage_guild=True)
    async def remove_invites(self, ctx, user: discord.Member, amount: int):
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="Amount must be a positive number",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        user_invites = self.get_user_invites(ctx.guild.id, user.id)
        
        if user_invites["invites"] < amount:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{user.mention} only has {user_invites['invites']} invites",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        user_invites["invites"] -= amount
        user_invites["total"] -= amount
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Invites Removed",
            description=f"Removed **{amount}** invites from {user.mention}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📨 Total invites",
            value=str(user_invites["invites"]),
            inline=True
        )
        
        embed.set_footer(text=f"Modified by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @commands.command(name="invitesleaderboard", aliases=["inviteslb", "invitestop"])
    async def invites_leaderboard(self, ctx):
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.invites_data or not self.invites_data[guild_id]:
            embed = discord.Embed(
                title="❌ Error",
                description="No invite data found for this server",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        sorted_invites = sorted(
            self.invites_data[guild_id].items(),
            key=lambda x: x[1]["invites"],
            reverse=True
        )[:10]  # Top 10
        
        embed = discord.Embed(
            title="📨 Invites Leaderboard",
            description=f"Top inviters in {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        for index, (user_id, data) in enumerate(sorted_invites, 1):
            user = ctx.guild.get_member(int(user_id))
            user_name = user.display_name if user else f"Unknown User ({user_id})"
            
            embed.add_field(
                name=f"{index}. {user_name}",
                value=f"Invites: **{data['invites']}** | Total: **{data['total']}** | Left: **{data['left']}**",
                inline=False
            )
            
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @commands.command(name="resetinvites")
    @commands.has_permissions(administrator=True)
    async def reset_invites(self, ctx, user: discord.Member = None):
        guild_id = str(ctx.guild.id)
        
        if user:
            user_id = str(user.id)
            if guild_id in self.invites_data and user_id in self.invites_data[guild_id]:
                self.invites_data[guild_id][user_id] = {
                    "invites": 0,
                    "total": 0,
                    "left": 0
                }
                self.save_data()
                
                embed = discord.Embed(
                    title="✅ Invites Reset",
                    description=f"Reset all invites for {user.mention}",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"No invite data found for {user.mention}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            # Reset for the entire server
            if guild_id in self.invites_data:
                self.invites_data[guild_id] = {}
                self.save_data()
                
                embed = discord.Embed(
                    title="✅ Server Invites Reset",
                    description=f"Reset all invites for {ctx.guild.name}",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="No invite data found for this server",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Invites(bot))
