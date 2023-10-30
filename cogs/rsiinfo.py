import asyncio
import gc
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
import time
import functools
from functools import lru_cache
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
        self.clear_lru_cache.start()

    @tasks.loop(hours=1)
    async def clear_lru_cache(self):
        objects = [i for i in gc.get_objects()  
                if isinstance(i, functools._lru_cache_wrapper)] 
        for object in objects: 
            object.cache_clear()

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

    @lru_cache(maxsize=32)
    def create_userinfo_embed(self, ign):
        user = RSIScraper.User(ign)
        embed = discord.Embed()
        if user.exists:
            embed.set_author(name=user.user_name, icon_url=user.media.profile_picture)
            embed.add_field(name='Account Age', value=f'Enlisted: {user.accountage.enlistment_date}\nAge: {user.accountage.str}')
            embed.add_field(name='Main Organization', value=f'Name: {user.organizations.main.name}')
        else:
            embed.add_field(name='Error', value=f'User "{ign}" not found')
        return embed

    @slash_command()
    async def user_info(self, ctx:discord.ApplicationContext, ingamename:str):
        try:
            embed = self.create_userinfo_embed(ingamename)
            await ctx.respond(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

    @user_command(name='Account Info', cog='rsiinfo')
    async def user_info_usercmd(self, ctx, user: discord.Member):
        try:
            ign = self.load_ign(user.id)
            if ign:
                embed = self.create_userinfo_embed(ign)
            else:
                embed = discord.Embed()
                embed.add_field(name='Error', value='User has not linked his account.')
            await ctx.respond(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

    @slash_command(name='linkaccount', description='Verbindet deine Discord ID mit deinem Ingame Namen')
    async def link_user_account(self, ctx, ingamename: str):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS users (discord_id INTEGER PRIMARY KEY,ingame_name TEXT)')
            c.execute('INSERT OR REPLACE INTO users (discord_id, ingame_name) VALUES (?, ?)', (ctx.author.id, ingamename))
            con.commit()
        await ctx.respond(f"Discord Account '{ctx.author.display_name} (ID: {ctx.author.id})' verbunden mit Nutzername {ingamename}",ephemeral=True)

    @slash_command()
    async def org_info(self, ctx:discord.ApplicationContext, org_tag: str):
        org = RSIScraper.Organization(org_tag)
        if org.exists:
            embeds = []
            embed = discord.Embed(title=org.name)
            members = discord.Embed(title=f'Members of {org.name}')
            memberstr = ',\n'.join(sorted(org.members.list))
            infostr = f'{len(org.members.list)} members\n'
            embed.add_field(name='Information', value=infostr)
            embed.set_footer(text=org.tag)
            embeds.append(embed)
            members.add_field(name=f'Members', value=memberstr)
            embeds.append(members)
            await ctx.respond(embeds=embeds, delete_after=10)
        else:
            embed = discord.Embed()
            embed.add_field(name='ERROR', value=f'Organization "{org_tag}" not found.')
            await ctx.respond(embed=embed, delete_after=10)

def setup(bot):
    logger.info(f"Cog {os.path.basename(__file__).replace('.py', '')} loaded")
    bot.add_cog(RSIInfo(bot))