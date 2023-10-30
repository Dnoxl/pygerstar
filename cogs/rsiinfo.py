import os
import sys
import io
import discord
import sqlite3
import re
import datetime
import traceback
import logging
import json
import requests 
from CogBase import Localization
from RSIScraper import RSIScraper
from bs4 import BeautifulSoup
from pprint import pprint
from collections import OrderedDict
from discord.ext import commands, tasks
from discord.commands import slash_command, Option, user_command
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

class RSIInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = Path(sys.path[0], 'bot.db')

    def load_ign(self, discord_id: int) -> str:
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                        discord_id INTEGER PRIMARY KEY,
                        ingame_name TEXT
                        )
                    ''')
            result = c.execute('SELECT ingame_name FROM users WHERE discord_id = ?', (discord_id,)).fetchone()
            ign = result[0] if result else None
        return ign

    def create_userinfo_embed(self, ign):
        user = RSIScraper.User(ign)
        embed = discord.Embed()
        embed.set_author(name=user.user_name, icon_url=user.fetch_profile_picture())
        embed.add_field(name='Account Age', value=f'Enlisted: {user.enlistment_date}\nAge: {user.account_age_str}')
        embed.add_field(name='Main Organization', value=f'Name: {user.main_organization}')
        return embed

    @slash_command()
    async def user_info(self, ctx:discord.ApplicationContext, ingamename:str):
        try:
            embed = self.create_userinfo_embed(ingamename)
            await ctx.respond(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

    @slash_command()
    async def self_info(self, ctx:discord.ApplicationContext):   
        try:
            ign = self.load_ign(ctx.author.id)
            embed = self.create_userinfo_embed(ign)
            await ctx.respond(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

def setup(bot):
    logger.info(f"Cog {os.path.basename(__file__).replace('.py', '')} loaded")
    bot.add_cog(RSIInfo(bot))