"""
TODO: Implement the confirmation view for a bounty kill
"""

"""
DOC:
BOUNTY STATES:
    0 - Open
    1 - Pending
    2 - Closed
"""

import os
import sys
import discord
import sqlite3
import traceback
import json
import time
import datetime
import logging
import ulid
from discord.ext import commands, tasks
from discord.commands import user_command, Option, slash_command
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

locales = ('en-US', 'de')
owners = [459747395027075095]

logger = logging.getLogger()

def is_authorized(**perms):
    '''Guild only'''
    original = commands.has_permissions(**perms).predicate
    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        return ctx.author.id in owners or await original(ctx)
    return commands.check(extended_check)

class Localization:
    '''The Localization class is used to load and assign localization strings from a JSON file based on a given locale.\nen-US as Fallback locale.'''
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

class KillConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green, custom_id='bounty_kill:confirm')
    async def confirm_button(self, button, interaction):
        pass

    @discord.ui.button(label='Deny', style=discord.ButtonStyle.red, custom_id='bounty_kill:deny')
    async def deny_button(self, button, interaction):
        pass

class Database:
    '''Handles the Database for the Bounties'''
    def __init__(self):
        self.db_path = Path(sys.path[0], 'bot.db')
        self.initialize_database()

    def initialize_database(self):
        '''Creates the Database if it doesn't exist'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS bounties (bounty_id INTEGER PRIMARY KEY AUTOINCREMENT, pending_id TEXT DEFAULT NULL, author_id INTEGER NOT NULL, killer_id INTEGER DEFAULT NULL, target TEXT NOT NULL, reward INTEGER NOT NULL CHECK(reward>0), status INTEGER NOT NULL DEFAULT 0, confirmed INTEGER NOT NULL DEFAULT 0, creation_time REAL NOT NULL, timeout_time REAL DEFAULT NULL)")
                con.commit()
        except:logger.error(traceback.format_exc())

#Command Backend
    def insert_bounty(self, author_id:int , target:str, reward:int)->bool:
        '''Inserts a bounty into the Database'''
        try:
            creation_time = time.time()
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("INSERT INTO bounties (author_id, target, reward, creation_time) VALUES (?,?,?,?)",(author_id,target,reward,creation_time,))
                con.commit()
                return True
        except:
            logger.error(traceback.format_exc())
            return False

    async def create_confirm_embed(self, ):
        pass

#Checking
    def target_exists(self, target:str)->bool:
        '''Checks whether the target exists'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("SELECT * FROM bounties WHERE target = ?",(target,))
            return c.fetchall()[0] is not None
        except:logger.error(traceback.format_exc())

#Data Retrieval
    def retr_bounty_count(self, target:str)->int:
        """
        The function retrieves the count of bounties with a specific target and status from a SQLite
        database.
        :return: an integer, which represents the count of bounties with a specific target and status
        from a SQLite database.
        """
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                count = c.execute("SELECT COUNT(target) FROM bounties WHERE status = 0 AND target = ?",(target,)).fetchone()[0]
            return count
        except:logger.error(traceback.format_exc())

    def retr_target_list(self)->list:
        """
        The function retrieves a list of distinct targets from a SQLite database where the status is 0.
        :return: a list of distinct targets from the "bounties" table in the SQLite database where the
        status is 0.
        """
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                targets = [row[0] for row in c.execute("SELECT DISTINCT target FROM bounties WHERE status = 0").fetchone()]
            return targets
        except:logger.error(traceback.format_exc())

    # Returns Author IDs of a target
    def retr_bounty_authors(self, target:str)->list:
        """
        The function retrieves the author IDs of bounties with a specific target and status from a
        SQLite database.
        :return: a list of author IDs.
        """
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                author_ids = [row for row in c.execute("SELECT author_id FROM bounties WHERE status = 0 AND target = ?",(target,)).fetchone()]
            return author_ids
        except:logger.error(traceback.format_exc())

    def retr_all_pending_bounties(self)->list:
        '''Returns all pending bounties'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                bounty_ids = [row for row in c.execute("SELECT bounty_id FROM bounties WHERE status = 1").fetchone()]
            return bounty_ids
        except:logger.error(traceback.format_exc())

    def retr_pending_bounties(self, target:str)->list:
        '''Returns all pending bounties for a target'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                bounty_ids = [row for row in c.execute("SELECT bounty_id FROM bounties WHERE target = ? AND status = 1",(target,)).fetchone()]
            return bounty_ids
        except:logger.error(traceback.format_exc())

    def retr_open_bounties(self, target:str)->list:
        '''Returns all open bounties for a target'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                bounty_ids = [row for row in c.execute("SELECT bounty_id FROM bounties WHERE target = ? AND status = 0",(target,)).fetchone()]
            return bounty_ids
        except:logger.error(traceback.format_exc())

    def retr_completed_bounties(self, target:str)->list:
        '''Returns all completed bounties for a target'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                bounty_ids = [row[0] for row in c.execute("SELECT bounty_id FROM bounties WHERE target = ? AND status = 2",(target,)).fetchone()]
            return bounty_ids
        except:logger.error(traceback.format_exc())

#Status Handling
    def set_completed(self, pending_id:str):
        '''Marks a bounty as completed'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("UPDATE bounties SET status = 2, pending_id = NULL, timeout_time = NULL WHERE pending_id = ?",(pending_id))
                con.commit()
        except:logger.error(traceback.format_exc())

    def set_pending(self, target:str, killer_id:int, pending_id):
        '''Generates a uuid pending_id, sets status to pending, creates a timeout and inserts the killer_id'''
        try:
            with sqlite3.connect(self.db_path) as con:
                timeout_time = time.time() + (48*60*60)
                c = con.cursor()
                bounty_ids = self.retr_open_bounties(target=target)
                for bounty in bounty_ids:
                    #Sets status to pending and sets it to timeout in 48hours
                    c.execute("UPDATE bounties SET status = 1, pending_id = ?, killer_id = ?, timeout_time = ? WHERE bounty_id = ?",(pending_id,killer_id,timeout_time,bounty,))
                    con.commit()
        except:logger.error(traceback.format_exc())

    @tasks.loop(minutes=1)
    async def timeout_handler(self):
        '''Resets a bounty to open state if it has not been confirmed within 48 hours'''
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                pending_bounties = self.retr_all_pending_bounties()
                if pending_bounties is not None:
                    for bounty in pending_bounties:
                        timeout_time = c.execute("SELECT timeout_time FROM bounties WHERE bounty_id = ?",(bounty,)).fetchone()[0]
                        if timeout_time < time.time():
                            c.execute("SELECT pending_id FROM bounties WHERE bounty_id = ?",(bounty,))
                            pending_id = c.fetchone()[0]
                            directory_path = Path(sys.path[0], 'media', 'evidence')
                            for file_name in os.listdir(directory_path):
                                if file_name.startswith(pending_id):
                                    os.remove(Path(directory_path,file_name))
                            c.execute("UPDATE bounties SET status = 0, pending_id = NULL, killer_id = NULL, timeout_time = NULL, confirmed = 0 WHERE bounty_id = ?",(bounty,))
                            con.commit()
        except:logger.error(traceback.format_exc())

class Bounty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = Path(sys.path[0], 'bot.db')
        self.db = Database()
        self.db.timeout_handler.start()
        self.init_viewdb()

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.bot.add_view(KillConfirmationView())
        except:logger.error(traceback.format_exc())

    def init_viewdb(self):
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS persistent_views (view_name TEXT NOT NULL, channel_id INTEGER NOT NULL, message_id INTEGER NOT NULL)")
                con.commit()
        except:logger.error(traceback.format_exc())

    kopfgeld = discord.SlashCommandGroup(name='bounty',name_localizations={'de':'kopfgeld'})

    @kopfgeld.command(name='create', name_localizations={'de':'erstellen'})
    async def create_bounty(self, ctx:discord.ApplicationContext, target:Option(str, name_localizations={'de':'ziel'}), reward:Option(int, name_localizations={'de':'belohnung'})):
        try:
            success = self.db.insert_bounty(author_id=ctx.author.id, target=target, reward=reward)
            if not success:
                await ctx.respond('There was an error creating the bounty.', ephemeral=True, delete_after=60)
                return
            count = self.db.retr_bounty_count(target=target)-1
            embed = discord.Embed(title=f'Bounty for {target}', color=0x7d2222)
            if count > 0:
                if count == 1:
                    embed.set_footer(text=f'There is already one bounty for this target')
                else:
                    embed.set_footer(text=f'There are already {count} bounties for this target')
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.add_field(name='Target',value=target)
            embed.add_field(name='Reward', value=f'{reward} aUEC')
            await ctx.respond(embed=embed, delete_after=60)
        except:logger.error(traceback.format_exc())

    @kopfgeld.command(name='complete')
    async def complete_bounty(self, ctx:discord.ApplicationContext, target:Option(str, name_localizations={'de':'ziel'}), evidence:Option(discord.Attachment, name_localizations={'de':'beweis'})):
        try:
            await ctx.defer()
            if not self.db.target_exists(target=target):
                await ctx.interaction.response.send_message(f'No bounty was found for {target}', ephemeral=True, delete_after=30)
                return
            type = str(evidence.content_type).split('/',1)
            if not 'video' in type and not 'image' in type:
                await ctx.interaction.followup.send(f'Wrong media format.', ephemeral=True, delete_after=10)
                return
            pending_id = str(ulid.new().timestamp())
            file_ext = os.path.splitext(evidence.filename)[-1]
            file_path = Path(sys.path[0], 'media', 'evidence', f'{pending_id}{file_ext}')     
            await evidence.save(fp=file_path)
            self.db.set_pending(target=target, killer_id=ctx.author.id, pending_id=pending_id)
            await ctx.interaction.followup.send(file=await evidence.to_file(),  delete_after=10)
            #embed = await self.db.create_confirm_embed(pending_id=pending_id, )
        except:logger.error(traceback.format_exc())

def setup(bot):
    logger.info(f"Cog {os.path.basename(__file__).replace('.py', '')} loaded")
    bot.add_cog(Bounty(bot))
    