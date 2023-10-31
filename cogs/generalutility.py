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
from CogBase import Localization
from discord.ext import commands, tasks
from discord.commands import slash_command, Option
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

file_name = os.path.basename(__file__).split('.py')[0]

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

class GeneralUtility(commands.Cog):
    def __init__(self, bot:discord.Bot):
        self.bot = bot
        super().__init__()
        self.clear_msgs.description_localizations = {locale: Localization(file_name, locale).clear_msgs.command_desc for locale in locales}
        self.get_guildicon.description_localizations = {locale: Localization(file_name, locale).get_guildicon.command_desc for locale in locales}
        self.get_avatar.description_localizations = {locale: Localization(file_name, locale).get_avatar.command_desc for locale in locales}

    utility = discord.SlashCommandGroup('utility')

    @commands.Cog.listener()
    async def on_ready(self):
        [setattr(option, 'description_localizations', {locale: Localization(file_name, locale).clear_msgs.amount_desc for locale in locales}) for option in self.clear_msgs.options if option.name == 'amount']
        [setattr(option, 'name_localizations', {locale: Localization(file_name, locale).clear_msgs.amount_name for locale in locales}) for option in self.clear_msgs.options if option.name == 'amount']
        [setattr(option, 'description_localizations', {locale: Localization(file_name, locale).get_avatar.member_desc for locale in locales}) for option in self.get_avatar.options if option.name == 'user']
        [setattr(option, 'name_localizations', {locale: Localization(file_name, locale).get_avatar.member_name for locale in locales}) for option in self.get_avatar.options if option.name == 'user']

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
            loc = Localization(file_name, ctx.interaction.locale)
            await ctx.defer()
            amount+=1
            messages = []
            async for msg in ctx.channel.history(limit=amount):
                messages.append(msg)
                if len(messages) == amount:
                    break
            amount = len(messages)-1
            for msg in messages:
                try:
                    await msg.delete()
                except:
                    continue
            if amount == 1:
                await ctx.send(loc.clear_msgs.deleted_message, delete_after=10)
            else:
                await ctx.send(loc.clear_msgs.deleted_messages.format(amount), delete_after=10)
        except:
            logger.error(traceback.format_exc())
        
    #localization: MissingPermissions, NotOwner
    async def cog_command_error(self, ctx, error):
        """
        The function `cog_command_error` handles errors that occur during command execution and sends an
        appropriate response based on the type of error.
        """
        try:
            loc = Localization(file_name, ctx.interaction.locale)
            if isinstance(error, MissingPermissions):
                await ctx.respond(loc.cog_command_error.MissingPermissions, ephemeral=True)
            if isinstance(error, NotOwner):
                await ctx.respond(loc.cog_command_error.NotOwner, ephemeral=True)
        except:logger.error(traceback.format_exc())
            
def setup(bot):
    logger.info(f"Cog {os.path.basename(__file__).replace('.py', '')} loaded")
    bot.add_cog(GeneralUtility(bot))