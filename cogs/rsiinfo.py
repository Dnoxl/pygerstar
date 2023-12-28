import asyncio
import gc
import os
import sys
import discord
import sqlite3
import traceback
import logging
import time
import functools
from functools import lru_cache
from CogBase import Localization
from RSIScraper import RSIScraper
from discord.ext import commands, tasks
from discord.ext.pages import Paginator, Page
from discord.ext.commands import MissingPermissions, NotOwner
from discord.commands import slash_command, Option, user_command
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

class Tools:
    @lru_cache()
    async def create_userinfo_embed(self, ign):
        user = RSIScraper.User(ign)
        await user.initialize()
        embed = discord.Embed()
        mainorg = user.organizations.main
        if user.exists:
            mainorgstr = f'**Name**: {mainorg.name}\n***SID: [{mainorg.tag}]({mainorg.URL})***\n**Membercount**: {mainorg.members.amount}\n**Rank**: {mainorg.rank} (Rank {mainorg.rank_tier})' if mainorg.exists else 'NO MAIN ORG'
            embed.set_author(name=user.name)
            embed.add_field(name='Account Age', value=f'**Enlisted**: {user.accountage.enlistment_date}\n**Age**: {user.accountage.str}')
            embed.add_field(name='Main Organization', value=mainorgstr)
        else:
            embed.add_field(name='ERROR', value=f'User "{ign}" not found')
        return embed, mainorg.tag, mainorg.exists, mainorg
    
    @lru_cache
    async def create_orginfo_embeds(self, org_tag, org=None) -> list:
        try:
            if org is None:
                org = RSIScraper.Organization(org_tag)
                await org.initialize()
            pages = []
            if org.exists:
                total_members = len(org.members.dict)
                embed = discord.Embed(title=org.name)
                infostr = f'Members: {org.members.amount}\nRedacted: {org.members.redacted_count}\nHidden: {org.members.hidden_count}'
                embed.add_field(name='Information', value=infostr)
                embed.set_footer(text=org.tag)
                memberstr = ''
                member_index = 0
                for i, (k, v) in enumerate(org.members.dict.items()):
                    append_str = f'**{k}**, {v[0]} (Rank {v[1]})\n'
                    if i == total_members - 1:
                        memberstr += append_str
                    if len(memberstr)+len(append_str) >= 1024 or member_index >= 15 or i == total_members - 1:
                        members = discord.Embed(title=f'Members of {org.name}')
                        members.add_field(name=f'Members', value=memberstr)
                        pages.append(Page(embeds=[embed, members]))
                        memberstr = ''
                        member_index = 0
                    member_index += 1
                    memberstr += append_str
            else:
                embed = discord.Embed()
                embed.add_field(name='ERROR', value=f'Organization "{org_tag}" not found.')
                pages = [embed]
            return pages
        except:
            logger.error(traceback.format_exc())

class OrgInfoView(discord.ui.View):
    def __init__(self, org_tag, org=None):
        super().__init__(timeout=None)
        self.org_tag = org_tag
        self.org = org

    @discord.ui.button(label='Organization Info')
    async def website_callback(self, button:discord.Button, interaction:discord.Interaction):
        try:
            self.website_callback
            await interaction.response.defer()
            if self.org is None:
                pages = await Tools().create_orginfo_embeds(self.org_tag)
            else:
                pages = await Tools().create_orginfo_embeds(self.org_tag, self.org)
            paginator = Paginator(pages=pages, author_check=False, disable_on_timeout=True)
            msg = await paginator.respond(interaction)
            await asyncio.sleep(60)
            await msg.delete()
        except:logger.error(traceback.format_exc())
        
class RSIInfo(commands.Cog):
    def __init__(self, bot=None):
        self.bot = bot
        self.db_path = Path(sys.path[0], 'bot.db')
        self.clear_lru_cache.start()

    @tasks.loop(hours=6)
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

    @slash_command()
    async def user_info(self, ctx:discord.ApplicationContext, ingamename:str):
        try:
            await ctx.defer()
            s = time.perf_counter() # Startpoint
            embed, org_tag, exists, mainorg = await Tools().create_userinfo_embed(ingamename)
            logger.info(f'Userinfo for {ingamename} took {round(time.perf_counter()-s, 2)}s') # Endpoint
            await ctx.followup.send(embed=embed, delete_after=60, view=OrgInfoView(org_tag=org_tag, org=mainorg)) if exists else await ctx.followup.send(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

    @user_command(name='Account Info', cog='rsiinfo')
    async def user_info_usercmd(self, ctx:discord.ApplicationContext, user: discord.Member):
        try:
            await ctx.defer()
            ign = self.load_ign(user.id)
            if ign:
                s = time.perf_counter() # Startpoint
                embed, org_tag, exists, mainorg = await Tools().create_userinfo_embed(ign)
                logger.info(f'Userinfo for {ign} took {round(time.perf_counter()-s, 2)}s') # Endpoint
            else:
                embed = discord.Embed()
                embed.add_field(name='ERROR', value='User has not linked his account.')
            await ctx.followup.send(embed=embed, delete_after=60, view=OrgInfoView(org_tag=org_tag, org=mainorg)) if exists else await ctx.followup.send(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

    @slash_command(name='linkingamename', description='Verbindet deine Discord ID mit deinem Ingame Namen')
    async def link_user_account(self, ctx, ingamename: str):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS users (discord_id INTEGER PRIMARY KEY,ingame_name TEXT)')
            c.execute('INSERT OR REPLACE INTO users (discord_id, ingame_name) VALUES (?, ?)', (ctx.author.id, ingamename))
            con.commit()
        await ctx.respond(f"Discord Account '{ctx.author.display_name} (ID: {ctx.author.id})' verbunden mit Nutzername {ingamename}",ephemeral=True)

    @slash_command()
    async def org_info(self, ctx: discord.ext.commands.Context, org_tag: str):
        try:
            await ctx.defer()
            s = time.perf_counter() # Startpoint
            pages = await Tools().create_orginfo_embeds(org_tag)
            logger.info(f'Orginfo for {org_tag} took {round(time.perf_counter()-s, 2)}s') # Endpoint
            paginator = Paginator(pages=pages, author_check=False, disable_on_timeout=True) 
            msg = await paginator.respond(ctx.interaction)
            await asyncio.sleep(60)
            await msg.delete()
        except:logger.error(traceback.format_exc())

def setup(bot):
    logger.info(f"Cog {os.path.basename(__file__).replace('.py', '')} loaded")
    bot.add_cog(RSIInfo(bot))