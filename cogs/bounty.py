"""
TODO: Constructor of BountyData: Lists of pending bounties etc.
"""

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

class BountyData:
    def __init__(self):
        try:
            with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
                c = con.cursor()
                self.open_bounties = [row[0] for row in c.execute('SELECT bounty_id FROM bounties WHERE status = 0').fetchall()]
                self.pending_bounties = [row[0] for row in c.execute('SELECT bounty_id FROM bounties WHERE status = 1').fetchall()]
                self.closed_bounties = [row[0] for row in c.execute('SELECT bounty_id FROM bounties WHERE status = 2').fetchall()]
                self.targets = [row[0] for row in c.execute('SELECT DISTINCT target FROM bounties').fetchall()]
                self.target_authors = {target: [row[0] for row in c.execute('SELECT DISTINCT author_id FROM bounties WHERE target=?',(target,)).fetchall()] for target in self.targets}
                self.target_ids = {target: [row[0] for row in c.execute('SELECT bounty_id FROM bounties WHERE target=? AND status = 0',(target,)).fetchall()] for target in self.targets}
            self.attribute_dict = {attr: val for val in vars(self).values() for attr in vars(self).keys()}
        except:logger.error(traceback.format_exc())

    def print_attributes(self):
        for attr, val in vars(self).items():
            if not attr == 'attribute_dict':
                print(f"{attr}: {val}")

class BountySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    logger.info(f"Cog {os.path.basename(__file__).replace('.py', '')} loaded")
    bot.add_cog(BountySystem(bot))