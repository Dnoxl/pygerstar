"""
TODO: Add commands to display user/server information
"""

import os
import sys
import io
import discord
import logging
import traceback
import json
import asyncio
from discord.ext import commands, tasks
from discord.commands import slash_command, Option
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

locales = ('en-US', 'de')
owners = [459747395027075095]

logger = logging.getLogger()

def is_authorized(**perms):
    original = commands.has_permissions(**perms).predicate
    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        return ctx.author.id in owners or await original(ctx)
    return commands.check(extended_check)

class Localization:
    def __init__(self, locale):
        """
        The function initializes an object with a given locale, loads a JSON file corresponding to that
        locale, and assigns localization values.
        """
        try:
            super().__init__()
            self.locale = locale
            self.file_name = os.path.basename(__file__).split('.py')[0]
            self.json_content = self.load_locale_file(locale)
            self.assign_localization()
        except:logger.error(traceback.format_exc())
    
    def load_locale_file(self, locale):
        try:
            if not os.path.exists(Path(sys.path[0], 'Localization', f'{locale}-locale.json')):
                locale = 'en-US'
            with open(Path(sys.path[0], 'Localization', f'{locale}-locale.json')) as f:
                j = json.loads(f.read())
            return j
        except:logger.error(traceback.format_exc())
        
    def assign_localization(self):
            try:
                base_content = self.json_content[self.file_name]
                for function, values in base_content.items():
                    setattr(self, function, self._NestedClass(values))
            except:logger.error(traceback.format_exc())

    class _NestedClass:
        def __init__(self, values):
            try:
                for k, v in values.items():
                    setattr(self, k, v)
            except:logger.error(traceback.format_exc())

class GeneralUtility(commands.Cog):
    def __init__(self, bot:discord.Bot):
        self.bot = bot
        super().__init__()
        self.clear_msgs.description_localizations = {locale: Localization(locale).clear_msgs.command_desc for locale in locales}
        self.get_guildicon.description_localizations = {locale: Localization(locale).get_guildicon.command_desc for locale in locales}
        self.get_avatar.description_localizations = {locale: Localization(locale).get_avatar.command_desc for locale in locales}

    utility = discord.SlashCommandGroup('utility')

    @commands.Cog.listener()
    async def on_ready(self):
        [setattr(option, 'description_localizations', {locale: Localization(locale).clear_msgs.amount_desc for locale in locales}) for option in self.clear_msgs.options if option.name == 'amount']
        [setattr(option, 'name_localizations', {locale: Localization(locale).clear_msgs.amount_name for locale in locales}) for option in self.clear_msgs.options if option.name == 'amount']
        [setattr(option, 'description_localizations', {locale: Localization(locale).get_avatar.member_desc for locale in locales}) for option in self.get_avatar.options if option.name == 'user']
        [setattr(option, 'name_localizations', {locale: Localization(locale).get_avatar.member_name for locale in locales}) for option in self.get_avatar.options if option.name == 'user']

    @utility.command(name='servericon', description='Fetches the servers Icon.', guild_only=True)
    #localization: command_desc
    async def get_guildicon(self, ctx):
        try:
            await ctx.respond(ctx.guild.icon.url)
        except:logger.error(traceback.format_exc())

    @utility.command(name='useravatar', description='Fetches a users avatar.')
    #localization: command_desc, member_name, member_desc
    async def get_avatar(self, ctx, user: Option(discord.Member)):
        try:
            await ctx.respond(user.avatar.url)
        except:logger.error(traceback.format_exc())

    @utility.command(name='clear',description='Clears a specified amount of messages from the channel.', guild_only=True)
    @commands.check(is_authorized(administrator=True))
    #localization: command_desc, deleted_message, deleted_messages, amount_desc, amount_name
    async def clear_msgs(self, ctx:discord.ApplicationContext, amount: Option(int, description='The maximum amount of messages to clear.')):
        try:
            loc = Localization(ctx.locale)
            await ctx.defer()
            msg_count = 0
            async for msg in ctx.channel.history(limit=amount):
                msg_count += 1
                if msg_count == amount:
                    break
            if msg_count < amount:
                amount = msg_count
            await ctx.channel.purge(limit=amount)
            if amount == 1:
                await ctx.respond(loc.clear_msgs.deleted_message, ephemeral=True, delete_after=10)
            else:
                await ctx.respond(loc.clear_msgs.deleted_messages.format(amount), ephemeral=True, delete_after=10)
        except:
            logger.error(traceback.format_exc())
        
    #localization: MissingPermissions, NotOwner
    async def cog_command_error(self, ctx, error):
        """
        The function `cog_command_error` handles errors that occur during command execution and sends an
        appropriate response based on the type of error.
        """
        try:
            loc = Localization(ctx.locale)
            if isinstance(error, MissingPermissions):
                await ctx.respond(loc.cog_command_error.MissingPermissions, ephemeral=True)
            if isinstance(error, NotOwner):
                await ctx.respond(loc.cog_command_error.NotOwner, ephemeral=True)
        except:logger.error(traceback.format_exc())
            
def setup(bot):
    bot.add_cog(GeneralUtility(bot))