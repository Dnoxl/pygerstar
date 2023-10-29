"""
TODO: Clean up ConfigAboutme
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

# The `ConfigAboutme` class is a Discord UI view that allows users to add or remove fields from their
# personal About Me information.
class ConfigAboutme(discord.ui.View):  
    def __init__(self, user_id:int, locale):
        try:
            self.locale = locale
            super().__init__(timeout=30)
            self.user_id = user_id
            self.db_path = Path(sys.path[0], 'bot.db')
            infos = ['name', 'birthday', 'country', 'hobbies']
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
                for info in infos:
                    if not check_info(info, user_id):
                        c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (user_id, info,))
                con.commit()
                self.remops = [row[0] for row in c.execute('SELECT info FROM aboutme WHERE user_id = ? AND toggle = 1',(user_id,)).fetchall()]
                self.addops = [row[0] for row in c.execute('SELECT info FROM aboutme WHERE user_id = ? AND toggle = 0',(user_id,)).fetchall()]
                self.addselect.options = [discord.SelectOption(label=info, value=info) for info in self.addops] if self.addops else self.addselect.options
                self.addselect.disabled = not self.addops
                self.removeselect.options = [discord.SelectOption(label=info, value=info) for info in self.remops] if self.remops else self.removeselect.options
                self.removeselect.disabled = not self.remops
                self.addselect.placeholder = Localization(self.locale).addselect.placeholder
                self.removeselect.placeholder = Localization(self.locale).removeselect.placeholder
        except:logger.error(traceback.format_exc())
    
    @discord.ui.select(placeholder='Add a field to your Aboutme', options=[discord.SelectOption(label='Select an option', value='Placeholder')], row=0)
    #localization: placeholder
    async def addselect(self, select, interaction):
        """
        The function `addselect` updates a database record, modifies a list of options, and edits a
        message in response to a user interaction.
        """
        try:
            select.disabled=False
            selval = select.values[0]
            with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
                c = con.cursor()
                c.execute('UPDATE aboutme SET toggle = ? WHERE user_id = ? AND info = ?', (1, self.user_id, selval,))
                con.commit()
            self.addselect.options = [option for option in self.addselect.options if option.value != selval]
            await interaction.response.edit_message(view=ConfigAboutme(self.user_id, self.locale))
        except:logger.error(traceback.format_exc())

    @discord.ui.select(placeholder='Remove a field from your Aboutme', options=[discord.SelectOption(label='Select an option', value='Placeholder')], row=1)
    #localization: placeholder
    async def removeselect(self, select, interaction):
        """
        The function `removeselect` updates a database and removes an option from a select menu in a
        Discord interaction.
        """
        try:
            select.disabled=False
            selval = select.values[0]
            with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
                c = con.cursor()
                c.execute('UPDATE aboutme SET toggle = ? WHERE user_id = ? AND info = ?', (0, self.user_id, selval,))
                con.commit()
            self.removeselect.options = [option for option in self.removeselect.options if option.value != selval]
            await interaction.response.edit_message(view=ConfigAboutme(self.user_id, self.locale))
        except:logger.error(traceback.format_exc())
    
# The `AboutModal` class is a Discord UI modal that allows users to input and display information
# about themselves.
class AboutModal(discord.ui.Modal):
    def __init__(self, user_id:int):
        self.db_path = Path(sys.path[0], 'bot.db')
        self.user_id = user_id
        super().__init__(title='About you:')
        infos = ['name', 'birthday', 'country', 'hobbies']
        info_dict = OrderedDict()
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
                for info in infos:
                    if not check_info(info, user_id):
                        c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (self.user_id, info,))
                con.commit()
                rows = list(
                    c.execute(
                        'SELECT info, value FROM aboutme WHERE user_id = ? AND toggle = 1',
                        (self.user_id,),
                    ).fetchall()
                )
                for row in rows:
                    info, value = row
                    info_dict[info] = value
                info_dict = OrderedDict((info, info_dict[info]) for info in infos if info in info_dict)
            for info in info_dict.keys():
                if info == 'birthday':
                    label = info
                    label += '(dd.mm.yyyy)'
                    self.add_item(discord.ui.InputText(label=label, value=info_dict[info]))
                    continue
                self.add_item(discord.ui.InputText(label=info, value=info_dict[info]))
        except:logger.error(traceback.format_exc())
            
    #localization: embed_author
    async def callback(self, interaction:discord.Interaction):
        """
        The `aboutmodal_callback` function updates the user's information in a database and sends an
        embed message with the updated information.
        """
        try:
            values = {}
            for child in self.children:
                if isinstance(child, discord.ui.InputText):
                    if 'birthday' in child.label:
                        child.label = child.label.replace('(dd.mm.yyyy)', '')
                    values[child.label] = child.value
            embed = discord.Embed()
            print('hi')
            embed.set_author(name=Localization(interaction.locale).callback.embed_author.format(interaction.user.display_name), icon_url=interaction.user.display_avataravatar)
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                for value in values:
                    c.execute('UPDATE aboutme SET value = ? WHERE info = ? AND user_id = ?', (values[value], value, self.user_id,))
                    if value == 'birthday' and values[value] is not None:
                        age = age_from_string(values[value])
                        if age is not None:
                            embed.add_field(name='age', value=age)
                    embed.add_field(name=value, value=values[value])
                con.commit()
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        except:logger.error(traceback.format_exc())

# The `Social` class is a Python class that defines commands and listeners for managing user profiles
# and displaying information about users.
class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = Path(sys.path[0], 'bot.db')
        self.aboutme_config.description_localizations = {locale: Localization(locale).aboutme_config.command_desc for locale in locales}
        self.update_aboutme.description_localizations = {locale: Localization(locale).update_aboutme.command_desc for locale in locales}
        self.about_user.description_localizations = {locale: Localization(locale).about_user.command_desc for locale in locales}
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
        
    @commands.Cog.listener(name='on_ready')
    async def assign_attrs(self):
        [setattr(option, 'description_localizations', {locale: Localization(locale).about_user.user_desc for locale in locales}) for option in self.about_user.options if option.name == 'user']
        [setattr(option, 'name_localizations', {locale: Localization(locale).about_user.user_name for locale in locales}) for option in self.about_user.options if option.name == 'user']

    @commands.Cog.listener()
    async def on_ready(self):
        """
        The function initializes a SQLite database table called "aboutme" and inserts default values for
        certain information fields for each user in the bot's user list.
        """
        try:
            infos = ['name', 'birthday', 'country', 'hobbies']
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
                for user in self.bot.users:
                    for info in infos:
                        if not check_info(info, user.id):
                            c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (user.id, info,))
                con.commit()
        except:logger.error(traceback.format_exc())

    aboutme = discord.SlashCommandGroup('aboutme')

    @aboutme.command(name='configure', description= 'Choose what information you want to display.')
    #localization: command_desc
    async def aboutme_config(self, ctx):
        """
        The `aboutme_config` function is an asynchronous function that takes a `ctx` parameter and
        responds with a view called `ConfigAboutme` for the user specified by the `ctx.author.id`.
        """ 
        try:
            await ctx.respond(view=ConfigAboutme(user_id=ctx.author.id, locale=ctx.interaction.locale), ephemeral=True, delete_after=30)
        except:logger.error(traceback.format_exc())

    @aboutme.command(name='write',description='Write some Information about yourself.')    
    #localization: command_desc
    async def update_aboutme(self, ctx):
        """
        The function `update_aboutme` is an asynchronous function that takes a `ctx` parameter and sends
        a modal with the user's ID.
        """
        try:
            await ctx.send_modal(AboutModal(ctx.author.id))
        except:logger.error(traceback.format_exc())
        
    @user_command(name='Aboutme', cog='social')
    async def usercmd_about_user(self, ctx, user: discord.Member):
        """
        This function is used to display the "About Me" information of a user in a Discord embed.
        """
        try:
            embed = create_aboutme_embed(user, ctx.interaction.locale)
            await ctx.respond(embed=embed, delete_after=30)
        except:logger.error(traceback.format_exc())

    @aboutme.command(name='user', description='Show the Aboutme of another user.')
    #localization: command_desc, user_name, user_desc
    async def about_user(self, ctx, user: Option(discord.Member, description='User whose Aboutme you want to see.')):
        """
        This function is used to display the "About Me" information of a user in a Discord embed.
        """
        try:
            embed = create_aboutme_embed(user, ctx.interaction.locale)
            await ctx.respond(embed=embed, delete_after=30)
        except:logger.error(traceback.format_exc())
        
    @aboutme.command(name='self', description='Show the About Me of yourself.')
    async def about_self(self, ctx: discord.ApplicationContext):
        """
        The `about_self` function creates an embed with information about the author of a Discord message
        and sends it as a response.
        """
        try:
            user = ctx.author
            embed = create_aboutme_embed(user, ctx.interaction.locale)
            await ctx.respond(embed=embed, delete_after=30)
        except:logger.error(traceback.format_exc())

    async def cog_command_error(self, ctx, error):
        """
        The function `cog_command_error` handles specific errors that may occur during command execution
        and sends an appropriate response to the user.
        """
        try:
            if isinstance(error, MissingPermissions):
                await ctx.respond("You don't have permission to use this command.", ephemeral=True, delete_after=10)
            if isinstance(error, NotOwner):
                await ctx.respond("You are not my Owner.", ephemeral=True, delete_after=10)     
        except:logger.error(traceback.format_exc())   

def create_aboutme_embed(user: discord.User, locale):
    """
    The function `create_aboutme_embed` creates an embed object containing information about a user's
    profile.
    """
    try:
        infos = ['name', 'birthday', 'country', 'hobbies']
        info_dict = OrderedDict()
        embed = discord.Embed()
        age = ''
        with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
            c = con.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
            for info in infos:
                if not check_info(info, user.id):
                    c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (user.id, info,))
            con.commit()
            rows = list(
                c.execute(
                    'SELECT info, value FROM aboutme WHERE user_id = ? AND toggle = 1',
                    (user.id,),
                ).fetchall()
            )
            for row in rows:
                info, value = row
                info_dict[info] = value
            info_dict = OrderedDict((info, info_dict[info]) for info in infos if info in info_dict)
        for info in info_dict.keys():
            if info == 'birthday' and info_dict[info] is not None:
                age = age_from_string(info_dict[info])
                if age is not None:
                    embed.add_field(name='age', value=age)
            embed.add_field(name=info, value=info_dict[info])
        embed.set_author(name=Localization(locale).callback.embed_author.format(user.display_name), icon_url=user.display_avatar)
        return embed
    except:logger.error(traceback.format_exc())

def check_info(info: str, user_id:int) -> bool:
    """
    The function `check_info` checks if a given `info` exists in the `aboutme` table for a specific
    `user_id` in a SQLite database.
    """
    try:
        with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
            c = con.cursor()
            c.execute('SELECT * FROM aboutme WHERE info = ? AND user_id = ?', (info, user_id))
            result = c.fetchone()
            return result is not None and result[0] is not None
    except:logger.error(traceback.format_exc())

def age_from_string(date_string):
    """
    The function `age_from_string` takes a date string in the format "dd/mm/yyyy" and returns the age
    based on the current date.
    """
    try:
        pattern = r'^(0[1-9]|[12][0-9]|3[01])[./](0[1-9]|1[0-2])[./]\d{4}$'
        if re.match(pattern, date_string):
            day, month, year = map(int, re.split(r'[./]', date_string))
            birthdate = datetime.datetime(year, month, day)
            today = datetime.date.today()
            return (
                today.year
                - birthdate.year
                - ((today.month, today.day) < (birthdate.month, birthdate.day))
            )
        else:
            return None
    except:logger.error(traceback.format_exc())

def setup(bot):
    bot.add_cog(Social(bot))