"""
A module for helper functions called by other modules.

Depends on: constants, ErrorHandler, database
"""

# import libraries
import sys

# import discord.py
import discord
from discord import Interaction, app_commands
from discord.errors import HTTPException, Forbidden, NotFound
from discord.ext import commands

# import local constants
import ptn.boozebot.constants as constants
from ptn.boozebot.constants import bot

# import local modules
from ptn.boozebot.modules.ErrorHandler import CommandChannelError, CommandRoleError, CustomError, on_generic_error


# trio of helper functions to check a user's permission to run a command based on their roles, and return a helpful error if they don't have the correct role(s)
def getrole(ctx, id): # takes a Discord role ID and returns the role object
    role = discord.utils.get(ctx.guild.roles, id=id)
    return role

# helper for channel permission check
def getchannel(id):
    channel = bot.get_channel(id)
    return channel



def checkroles_actual(interaction: discord.Interaction | discord.ext.commands.Context, permitted_role_ids):
    if not isinstance(permitted_role_ids, list):
        permitted_role_ids = [permitted_role_ids]
    permission = False
    try:
        """
        Check if the user has at least one of the permitted roles to run a command
        """
        print(f"checkroles called.")
        if isinstance(interaction, discord.ext.commands.Context):
            author_roles = interaction.author.roles
        else:
            author_roles = interaction.user.roles
        permitted_roles = [getrole(interaction, role) for role in permitted_role_ids]
        print(author_roles)
        print(permitted_roles)
        permission = True if any(x in permitted_roles for x in author_roles) else False
        print(permission)
        return permission, permitted_roles
    except Exception as e:
        print(e)
    return permission
    
def check_channels_actual(interaction: discord.Interaction | discord.ext.commands.Context, permitted_channel_ids):
    if not isinstance(permitted_channel_ids, list):
        permitted_channel_ids = [permitted_channel_ids]
    permission = False
    try:
        """
        Check if the user is in a permitted channel to run a command
        """
        print(f"checkchannels_actual called.")
        author_channel = interaction.channel
        permitted_channels = [getchannel(id) for id in permitted_channel_ids]
        print(author_channel)
        print(permitted_channels)
        permission = True if any(x == author_channel for x in permitted_channels) else False
        print(permission)
        return permission, permitted_channels
    except Exception as e:
        print(e)
    return permission


def check_roles(permitted_role_ids):
    def decorator(func):
        func._permitted_roles = permitted_role_ids if isinstance(permitted_role_ids, list) else [permitted_role_ids]
        async def checkroles(interaction: discord.Interaction):
            permission, permitted_roles = checkroles_actual(interaction, permitted_role_ids)
            print("Inherited permission from checkroles")
            if not permission:
                formatted_role_list = " • ".join([f'<@&{role}> ' for role in permitted_role_ids])
                try:
                    raise CommandRoleError(permitted_roles, formatted_role_list)
                except CommandRoleError as e:
                    print(e)
                    raise
            return permission
        return app_commands.check(checkroles)(func)
    return decorator

def check_command_channel(permitted_channel_ids):
    def decorator(func):
        func._permitted_channels = permitted_channel_ids if isinstance(permitted_channel_ids, list) else [permitted_channel_ids]
        async def checkchannels(interaction: discord.Interaction):
            permission, permitted_channels = check_channels_actual(interaction, permitted_channel_ids)
            print("Inherited permission from checkchannels")
            if not permission:
                formatted_channel_list = " • ".join([f'<#{channel.id}> ' for channel in permitted_channels])
                try:
                    raise CommandChannelError(permitted_channels, formatted_channel_list)
                except CommandChannelError as e:
                    print(e)
                    raise
            return permission
        return app_commands.check(checkchannels)(func)
    return decorator

def check_text_command_roles(permitted_role_ids):
    def decorator(func):
        func._permitted_roles = permitted_role_ids  if isinstance(permitted_role_ids, list) else [permitted_role_ids]
        async def checkroles(ctx):
            permission, permitted_roles = checkroles_actual(ctx, permitted_role_ids)
            print("Inherited permission from checkroles")
            if not permission:
                await ctx.send("You do not have permission to run this command.")
            return permission
        return commands.check(checkroles)(func)
    return decorator

def check_text_command_channels(permitted_channel_ids):
    def decorator(func):
        func._permitted_channels = permitted_channel_ids if isinstance(permitted_channel_ids, list) else [permitted_channel_ids]
        async def checkchannels(ctx):
            permission, permitted_channels = check_channels_actual(ctx, permitted_channel_ids)
            print("Inherited permission from checkchannels")
            if not permission:
                formatted_channel_list = " • ".join([f'<#{channel.id}> ' for channel in permitted_channels])
                await ctx.send(f"You do not have permission to run this command in this channel. Please use one of the following channels: {formatted_channel_list}")
            return permission
        return commands.check(checkchannels)(func)
    return decorator

# function to stop and quit
def bot_exit():
    sys.exit("User requested exit.")