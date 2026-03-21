import os
from time import sleep

import discord
from dotenv import load_dotenv
from discord.ext import commands
from classes.database import Database
from classes.helpers import Helpers

class Updates(commands.Cog):
    """
    All slash commands that update information in database
    """
    def __init__(self, bot, database, helper):
        self._bot = bot
        self._database = database
        self._helper = helper

        self._char_list = []
        self._discord_list = []
        self._race_list = self._helper.get_races()
        self._class_list = self._helper.get_classes()
        self._tradekill_list = self._helper.get_tradeskills()
        self._type_list = self._helper.get_types()

    def get_char_list(self):
        return self._char_list

    def get_discord_list(self):
        return self._discord_list

    def set_char_list(self):
        self._char_list = self._database.get_all_char_names()

    def set_discord_list(self):
        self._discord_list = self._helper.get_all_discord_names('display')

    def update_lists(self):
        self._bot.get_cog("Lookups").set_name_list()
        self._bot.get_cog("Lookups").set_discord_list()
        self.set_char_list()
        self.set_discord_list()

    async def char_name_autocompletion(
            self,
            ctx: discord.AutocompleteContext,
    ):
        """
        Create a filtering list of char names
        :param ctx: the application context of the bot
        :return: filtered list
        """
        current_value = ctx.value

        if len(self.get_char_list()) == 0:
            self._char_list = self._database.get_all_char_names()

        return [choice for choice in self._char_list if current_value.lower() in choice.lower()]

    async def discord_name_autocompletion(
            self,
            ctx: discord.AutocompleteContext
    ):
        """
        Create a filtering list of discord names
        :param ctx: the application context of the bot
        :return: filtered list
        """
        current_value = ctx.value

        if len(self.get_discord_list()) == 0:
            self._discord_list = self._helper.get_all_discord_names('display')

        return [choice for choice in self._discord_list if current_value.lower() in choice.lower()]

    async def races_autocompletion(
            self,
            ctx: discord.AutocompleteContext
    ):
        """
        Create a filtering list of MnM races
        :param ctx: the application context of the bot
        :return: filtered list
        """
        current_value = ctx.value

        if len(self._race_list) == 0:
            self._race_list = self._helper.get_races()

        return [choice for choice in self._race_list if current_value.lower() in choice.lower()]

    async def classes_autocompletion(
            self,
            ctx: discord.AutocompleteContext
    ):
        """
        Create a filtering list of MnM classes
        :param ctx: the application context of the bot
        :return: filtered list
        """
        current_value = ctx.value

        if len(self._class_list) == 0:
            self._class_list = self._helper.get_classes()

        return [choice for choice in self._class_list if current_value.lower() in choice.lower()]

    async def tradeskills_autocompletion(
            self,
            ctx: discord.AutocompleteContext
    ):
        """
        Create a filtering list of MnM tradeskills
        :param ctx: the application context of the bot
        :return: filtered list
        """
        current_value = ctx.value

        if len(self._tradekill_list) == 0:
            self._tradekill_list = self._helper.get_tradeskills()

        return [choice for choice in self._tradekill_list if current_value.lower() in choice.lower()]

    async def types_autocompletion(
            self,
            ctx: discord.AutocompleteContext
    ):
        """
        Create a filtering list of database char types
        :param ctx: the application context of the bot
        :return: filtered list
        """
        current_value = ctx.value

        if len(self._type_list) == 0:
            self._type_list = self._helper.get_types()

        return [choice for choice in self._type_list if current_value.lower() in choice.lower()]

    @discord.slash_command(name="add_character", description="Add a character to the database")
    async def add_character(
            self,
            ctx: discord.ApplicationContext,
            discord_name: discord.Option(
                str,
                description='Discord display name',
                autocomplete=discord_name_autocompletion
            ),
            char_name: discord.Option(
                str,
                description='Monsters and Memories character name',
            ),
            char_type: discord.Option(
                str,
                description='Monsters and Memories character type',
                autocomplete=types_autocompletion
            ),
            char_race: discord.Option(
                str,
                description='Monsters and Memories character race',
                autocomplete=races_autocompletion,
                required=False
            ),
            char_class: discord.Option(
                str,
                description='Monsters and Memories character class',
                autocomplete=classes_autocompletion,
                required=False
            ),
            char_tradeskill: discord.Option(
                str,
                description='Monsters and Memories primary tradeskill',
                autocomplete=tradeskills_autocompletion,
                required=False
            )
    ):
        """
        Add a new character to bot database
        :param ctx: the application context of the bot
        :param discord_name: string selected from dropdown (required)
        :param char_name: string entered by user (required)
        :param char_race: string (all MnM races) selected from dropdown (optional)
        :param char_class: string (all MnM classes) selected from dropdown (optional)
        :param char_tradeskill: string (all MnM tradeskills) selected from dropdown (optional)
        :param char_type: string (main/alt/mule) selected from dropdown (optional)
        :return: none
        """
        await ctx.response.defer(ephemeral=True)

        # this slash command only available to officers
        target_role = discord.utils.get(ctx.guild.roles, name="Officer")

        # if validate_role returns false, user is not authorized,
        # so exit function
        if not self._helper.validate_role(ctx.author.roles, target_role):
            await self.not_authorized(ctx)
            return

        validation_check = self._helper.validate_entry(ctx.selected_options)

        if validation_check != "pass":
            await self.failed_validation(ctx, validation_check)
            return

        # this is checking the Discord guild list to see if
        # the discord id provided actually exists
        # i.e., is the discord id present on the server
        discord_id = self._helper.get_discord_id(discord_name, 'display')

        # if no discord id in database, notify user and exit
        if discord_id == "":
            await ctx.respond(
                f"```Discord ID not found for {discord_name}.\n"
                "Characters must have a valid Discord ID.```")
            return

        self._helper.log_activity(ctx.author, ctx.command, ctx.selected_options)

        # assign char_priority int based on char_type string
        # note: this is a hidden field in the database
        # it is purely for sorting purposes
        if char_type == "Main":
            char_priority = 0
        elif char_type == "Alt":
            char_priority = 1
        else:
            char_priority = 2

        try:
            results = self._database.insert_character(discord_id, char_name, char_race,
                                          char_class, char_tradeskill, char_type, char_priority)
            row = self._helper.get_row(results)

            # customize response message to user based on how
            # many character options were input
            message = f"({char_name} | "

            if char_race is not None:
                message = message + f"{char_race} | "

            if char_class is not None:
                message = message + f"{char_class} | "

            if char_tradeskill is not None:
                message = message + f"{char_tradeskill} | "

            # if char_type is not None:
            message = message + f"{char_type} | "

            # trim trailing pipe symbol and whitespace
            message = message[0:len(message) - 3]

            self.update_lists()
            await self.update_main_list(ctx, "")

            await ctx.respond(
                f"```{message}) entered."
                f"\n{results} {row} added to database.```"
            )
        except Exception as err:
            if "Duplicate entry" in str(err):
                await ctx.respond(f"{char_name} already exists in the database.")
            else:
                self._helper.log_activity(ctx.author, ctx.command, str(err))
                await ctx.respond(f"```An error has occurred: {err}.```")

    @discord.slash_command(name="edit_character", description="Edit an existing character")
    async def edit_character(
            self,
            ctx: discord.ApplicationContext,
            char_name: discord.Option(
                str,
                description='Original name',
                autocomplete=char_name_autocompletion
            ),
            new_name: discord.Option(
                str,
                description='New name',
                required=False
            ),
            char_race: discord.Option(
                str,
                description='New race',
                autocomplete=races_autocompletion,
                required=False
            ),
            char_class: discord.Option(
                str,
                description='New class',
                autocomplete=classes_autocompletion,
                required=False
            ),
            char_tradeskill: discord.Option(
                str,
                description='New primary tradeskill',
                autocomplete=tradeskills_autocompletion,
                required=False
            ),
            char_type: discord.Option(
                str,
                description='New type',
                autocomplete=types_autocompletion,
                required=False
            )
    ):
        """
        Edit an existing character in the database
        :param ctx: the application context of the bot
        :param char_name: string entered by user (required)
        :param new_name: string entered by user if name needs changed (optional)
        :param char_race: string (all MnM races) selected from dropdown (optional)
        :param char_class: string (all MnM classes) selected from dropdown (optional)
        :param char_tradeskill: string (all MnM tradeskills) selected from dropdown (optional)
        :param char_type: string (main/alt/mule) selected from dropdown (optional)
        :return: none
        """
        await ctx.response.defer(ephemeral=True)

        # this slash command only available to officers
        target_role = discord.utils.get(ctx.guild.roles, name="Officer")

        # if validate_role returns false, user is not authorized,
        # so exit function
        if not self._helper.validate_role(ctx.author.roles, target_role):
            await self.not_authorized(ctx)
            return

        # if ctx.selection_option is only 1, then user either
        # entered nothing after character name, or they did
        # not select from the slash command options
        # so exit function
        if len(ctx.selected_options) < 2:
            await ctx.respond(
                f"```No options selected.\n"
                f"Please try again.```")
            return

        validation_check = self._helper.validate_entry(ctx.selected_options)

        if validation_check != "pass":
            await self.failed_validation(ctx, validation_check)
            return

        self._helper.log_activity(ctx.author, ctx.command, ctx.selected_options)

        results = self._database.update_character(
            char_name, new_name, char_race, char_class, char_tradeskill, char_type
        )
        row = self._helper.get_row(results)

        # customize response message to user based on how
        # many edit options were input
        if results > 0:
            message = f"{char_name} updated to: "

            if new_name is not None:
                message = message + f"{new_name} | "

            if char_race is not None:
                message = message + f"{char_race} | "

            if char_class is not None:
                message = message + f"{char_class} | "

            if char_tradeskill is not None:
                message = message + f"{char_tradeskill} | "

            if char_type is not None:
                message = message + f"{char_type} | "

            # trim trailing pipe symbol and whitespace
            message = message[0:len(message) - 3]
        else:
            message = f"{char_name} not found"

        self.update_lists()
        await self.update_main_list(ctx, "")

        await ctx.respond(
            f"```{message}."
            f"\n{results} {row} updated in database.```")

    @discord.slash_command(name="delete_character", description="Delete a character")
    async def delete_character(
            self,
            ctx: discord.ApplicationContext,
            char_name: discord.Option(
                str,
                description='Monsters and Memories character name',
                autocomplete=char_name_autocompletion
            )
    ):
        """
        Delete a character from the database
        :param ctx: the application context of the bot
        :param char_name: string entered by user (required)
        :return: none
        """
        await ctx.response.defer(ephemeral=True)

        # this slash command only available to officers
        target_role = discord.utils.get(ctx.guild.roles, name="Officer")

        # if validate_role returns false, user is not authorized,
        # so exit function
        if not self._helper.validate_role(ctx.author.roles, target_role):
            await self.not_authorized(ctx)
            return

        self._helper.log_activity(ctx.author, ctx.command, ctx.selected_options)

        db_type = ""
        char_results = self._database.get_char_and_type(char_name)

        for char in char_results:
            db_type = char['char_type']

        results = self._database.delete_character(char_name)
        row = self._helper.get_row(results)

        # if results > 0 then query was successful
        # i.e., character was deleted
        if results > 0:
            message = f"You deleted: {char_name}"
        else:
            message = f"{char_name} not found"

        self.update_lists()

        if db_type == "Main":
            await self.update_main_list(ctx, db_type)

        await ctx.respond(
            f"```{message}."
            f"\n{results} {row} deleted from database.```")

    @discord.slash_command(
        name="update_main_list",
        description="Update Discord main list after edits"
    )
    async def update_main_list(
            self,
            ctx: discord.ApplicationContext,
            db_type
    ):
        char_name = ""
        cmd_type = ""

        for option in ctx.selected_options:
            if option['name'] == 'char_name':
                char_name = option['value']

            if option['name'] == 'char_type':
                cmd_type = option['value']

        if cmd_type == "" and db_type == "":
            char_results = self._database.get_char_and_type(char_name)

            for char in char_results:
                db_type = char['char_type']

        if cmd_type == 'Main' or db_type == 'Main':
            results = self._database.find_all_mains()
            main_list = (f"```Main characters in Firefly...\n"
                         f"\n{self._helper.format_main_message(results)}\n"
                         f"Total count of mains: {len(results)}```")

            channel = self._bot.get_channel(1484348927003201717)
            history = await channel.history(limit=1).flatten()

            if len(history) > 0:
                for item in history:
                    message_id = item.id
                    message = await channel.fetch_message(message_id)

                    await message.delete()

            await channel.send(main_list)

    async def not_authorized(
            self,
            ctx: discord.ApplicationContext
    ):
        # Display unauthorized message to user in Discord
        await ctx.respond(
            f"```You do not have permission to use this command.\n"
            f"Please try another command.```")

    async def failed_validation(
            self,
            ctx: discord.ApplicationContext,
            error_type
    ):
        # Display failed validation message to user in Discord
        await ctx.respond(
            f"```You must choose one of the available options for {error_type}.\n"
            f"Please try again.```")

def setup(bot):
    load_dotenv()

    guild = os.getenv('DISCORD_GUILD')
    helper = Helpers(bot, guild)
    database = Database()

    bot.add_cog(Updates(bot, database, helper))
