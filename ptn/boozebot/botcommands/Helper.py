"""
Steve's help command

"""

# libraries
import re
import enum
import logging

# discord.py
import discord
from discord.ext import commands
from discord import app_commands

# local constants
from ptn.boozebot.constants import get_steve_says_channel, get_wine_carrier_channel, wine_carrier_command_channel, \
    server_mod_role_id, server_sommelier_role_id, server_council_role_ids, server_connoisseur_role_id, server_wine_carrier_role_id, \
    bot_guild_id

# local modules
from ptn.boozebot.modules.ErrorHandler import on_app_command_error, GenericError, CustomError, on_generic_error
from ptn.boozebot.modules.helpers import bot_exit, check_roles, check_command_channel


"""
STEVE HELPER COMMAND

/pirate_steve_help - everyone
"""


# initialise the Cog and attach our global error handler
class Helper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.CATEGORY_ROLES = [server_council_role_ids()[0], server_sommelier_role_id(), server_connoisseur_role_id(), server_wine_carrier_role_id()]

    # custom global error handler
    # attaching the handler when the cog is loaded
    # and storing the old handler
    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = on_app_command_error

    # detaching the handler when the cog is unloaded
    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error

        
    # Fetch all the role names
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            guild = self.bot.get_guild(bot_guild_id())
        except Exception as e:
            logging.exception(f"Failed to get guild: {e}")


        self.commands_data = {}
        
        roles = await guild.fetch_roles()
        
        for command in self.bot.commands:
            command_data = {}
            command_data["name"] = command.qualified_name
            command_data["description"] = command.help if hasattr(command, "help") else "No description provided"
            command_data["roles"] = command.callback._permitted_roles if hasattr(command.callback, "_permitted_roles") else []
            command_data["channel_restrictions"] = command.callback._permitted_channels if hasattr(command.callback, "_permitted_channels") else []
            command_data["params"] = []
            command_data["type"] = "Text Command"
            command_data["invocation"] = f"b/{command.qualified_name}"
            
            permitted_roles = list(filter(lambda role: role in self.CATEGORY_ROLES, command_data["roles"]))
            lowest_role_id = permitted_roles[-1] if permitted_roles else None
                
            if lowest_role_id:
                try:
                    lowest_role_name = next((role.name for role in roles if role.id == lowest_role_id), None)
                except Exception as e:
                    logging.exception(f"Failed to get role: {e}")
            else:
                lowest_role_name = "Everyone"
            
            if self.commands_data.get(lowest_role_name) is None:
                self.commands_data[lowest_role_name] = []

            self.commands_data[lowest_role_name].append(command_data)

            
        for command in self.bot.tree.get_commands():
            
            if isinstance(command, discord.app_commands.Group):
                continue
            
            command_data = {}
            command_data["name"] = command.qualified_name
            command_data["description"] = command.description if hasattr(command, "description") else "No description provided"
            command_data["roles"] = command.callback._permitted_roles if hasattr(command.callback, "_permitted_roles") else []
            command_data["channel_restrictions"] = command.callback._permitted_channels if hasattr(command.callback, "_permitted_channels") else []
            command_data["params"] = []
            
            if isinstance(command, discord.app_commands.ContextMenu):
                command_data["type"] = "Context Menu"
                command_data["invocation"] = f"Context Menu: {command.qualified_name}"
            else:
                command_data["type"] = "Slash Command"
                command_data["invocation"] = f"/{command.qualified_name}"
            
            if command_data["type"] != "Context Menu":
                for param in command.parameters:
                    command_data["params"].append({
                        "name": param.display_name,
                        "description": param.description if hasattr(param, "description") else "No description provided",
                        "type": param.type,
                    })
            
            permitted_roles = list(filter(lambda role: role in self.CATEGORY_ROLES, command_data["roles"]))
            lowest_role_id = permitted_roles[-1] if permitted_roles else None
            
            if lowest_role_id:
                try:
                    lowest_role_name = next((role.name for role in roles if role.id == lowest_role_id), None)
                except Exception as e:
                    logging.exception(f"Failed to get role: {e}")
            else:
                lowest_role_name = "Everyone"
            
            if self.commands_data.get(lowest_role_name) is None:
                self.commands_data[lowest_role_name] = []

            self.commands_data[lowest_role_name].append(command_data)
      
    def buildHelpEmbed(self, command):
        """
        Function to send the help information for a specific command.

        :param dict command: The command information to send help for
        :returns: None
        """

        #Get command name and info from enum class
        commandName = command["name"]
        
        description = command["description"]
        roles = command["roles"]
        params = command["params"]
        channels = command["channel_restrictions"]
        
        channels = [f'<#{channel}>' for channel in channels]
        channelText = f'**Channel Restrictions**: {", ".join(channels)}.' if channels else ''
        
        roles = [f'<@&{role}>' for role in roles]
        roleText = f'**Required Roles**: {", ".join(roles)}.' if roles else ''
        
        response_embed = discord.Embed(
            title=f'Batten down the hatches!\nPirate Steve knows the following for: {commandName}.',
            description=f'**Invocation**: {command["invocation"]}\n'
                        f'**Description**: {description}\n'
                        f'{roleText}\n'
                        f'{channelText}\n'
                        f'**Params**: '
        )
        
        # Go build some fields for each param and log the information into it
        if params:
            for param in params:
                response_embed.add_field(
                    name=f'• {param["name"]}:',
                    value=f'- Description: {param["description"]}.\n'
                          f'- Type: {param["type"]}.',
                    inline=False
                )
        else:
            # In the case of no params, just append None to the description.
            response_embed.description += 'None.'
            
        return response_embed

   
    @app_commands.command(name="pirate_steve_help", description="Returns some information for each command.")
    async def get_help(self, interaction: discord.Interaction):
        
        print(f"pirate_steve_help called by {interaction.user.name} in {interaction.channel.name}")
                
        options = [
            discord.SelectOption(label=role, value=role)
            for role in self.commands_data.keys()
        ]
        role_select = discord.ui.Select(placeholder="Choose a role...", options=options)
        
        main_interaction = interaction

        async def select_callback(interaction: discord.Interaction):
            role = role_select.values[0]
            print(f"Role selected: {role}")
            commands = self.commands_data[role]
            command_options = [
                discord.SelectOption(label=cmd["name"], value=cmd["name"])
                for cmd in commands
            ]
            command_select = discord.ui.Select(placeholder="Choose a command...", options=command_options)

            async def command_select_callback(interaction: discord.Interaction):
                command_name = command_select.values[0]
                
                command = next((cmd for cmd in commands if cmd["name"] == command_name), None)
                print(f"Command selected: {command_name}")
                response_embed = self.buildHelpEmbed(command)
                print("Sending command information message")
                await interaction.response.defer()
                await main_interaction.edit_original_response(embed=response_embed, view=None)

            command_select.callback = command_select_callback
            view = discord.ui.View()
            view.add_item(command_select)
            print("Sending command selection message")
            await interaction.response.defer()
            await main_interaction.edit_original_response(content="Select a command:", view=view)

        role_select.callback = select_callback
        view = discord.ui.View()
        view.add_item(role_select)
        print("Sending role selection message")
        await interaction.response.send_message("Commands for role:", view=view, ephemeral=True)