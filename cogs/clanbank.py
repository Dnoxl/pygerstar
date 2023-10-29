import os
import sys
import discord
import sqlite3
import gspread
from pytz import timezone
from datetime import datetime
from discord.ext import commands
from discord.commands import slash_command, user_command, Option
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

class ClanBank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = curdir('bot.db')
        self.gc = gspread.service_account(filename=curdir('german-starmarine.json'))

    def selectfrom_settings(self, setting: str):     
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            val = c.execute('SELECT value FROM settings WHERE setting = ?',(setting,)).fetchone()[0]
        return val

    async def load_ign(self, discord_id: int) -> str:
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
    
    @slash_command(name='showign')
    async def send_ign(self, ctx, user: Option(discord.Member, required = False, default=None)):
        if user is None:
            user = ctx.author
        ign = await self.load_ign(user.id)
        if ign is not None:
            await ctx.respond(f'Der Ingame Name von {user.display_name} lautet: {ign}.',epehemeral=True)
        else:
            await ctx.respond(f'Der Nutzer {user.display_name} hat keinen Ingame Namen verbunden.',ephemeral=True)

    @slash_command(name='ignlink', description='Verbindet deine Discord ID mit deinem Ingame Namen')
    async def update_ignlink(self, ctx, ingamename: str):
        discordname = ctx.author.display_name
        discordid = ctx.author.id
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                        discord_id INTEGER PRIMARY KEY,
                        ingame_name TEXT
                        )
                    ''')
            c.execute('INSERT OR REPLACE INTO users (discord_id, ingame_name) VALUES (?, ?)', (discordid, ingamename))
            con.commit()
        await ctx.respond(f"Discord Account '{discordname} (ID: {discordid})' verbunden mit Nutzername {ingamename}",ephemeral=True)

    @slash_command(name='pay')
    async def pay(self, ctx, amount: Option(int, description='Der Betrag der Einzahlung')):  
        ign = await self.load_ign(ctx.author.id)
        date = datetime.now(timezone('Europe/Berlin')).strftime('%d.%m.%y')
        if ign is None:
            await ctx.respond(
                'Du hast keinen Ingame Namen verbunden. Bitte nutze /ignlink und versuche es erneut.',
                ephemeral=True,
            )
            return
        self.add_deposit(discordid=ctx.author.id, deposit=amount, date=date)
        await ctx.respond(f'Erfolgreich {amount} aUEC eingezahlt von {ign}. ({date})')
        await self.CreateEntry()
        
    @slash_command(name='databasewipe')
    @commands.has_guild_permissions(administrator=True)
    async def databasewipe(self,ctx):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('DELETE FROM deposits')
            c.execute('UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = "deposits"')
            con.commit()
        await self.CreateEntry()
        await ctx.respond('Clearing Database!',ephemeral=True)

    @slash_command(name='refresh', description='Refreshes the Spreadsheet.')
    async def refresh_sheet(self, ctx):
        await self.CreateEntry()
        await ctx.respond('Refreshing the Spreadsheet', ephemeral=True)

    async def CreateEntry(self):
        dids = self.load_discordids()
        cols = []
        rows = []
        entries = []
        for i, did in enumerate(dids):   
            data = self.load_deposits(discordid=did)
            deposits = []
            dates = []
            for d in data:
                deposits.append(d[0])
                dates.append(d[1])
            ign = await self.load_ign(discord_id=int(did))
            row = 3
            col1 = i*2 if i != 0 else i*2+1
            col2 = i*2+1 if i != 0 else i*2+2
            cols.extend([col1, col2])
            rows.extend([row, row])
            entries.extend((ign, 'aUEC'))
            for j, deposit in enumerate(deposits):
                row += 1
                cols.extend([col1, col2])
                rows.extend([row, row])
                entries.extend((dates[j], deposit))
        spreadsheet_key = self.selectfrom_settings(setting='spreadsheet_key')
        wks = self.gc.open_by_key(spreadsheet_key)
        sh = wks.sheet1
        sh.clear()
        for e, col in enumerate(cols):
            sh.update_cell(col=col, row=rows[e], value=entries[e])     

    def add_deposit(self, discordid: int, deposit: int, date: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''
                        CREATE TABLE IF NOT EXISTS deposits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id INTEGER,
                        deposit REAL,
                        date TEXT
                        )
                    ''')
            c.execute('INSERT INTO deposits (discord_id, deposit, date) VALUES (?, ?, ?)', (discordid, deposit, date))
            con.commit()

    def load_discordids(self) -> list:
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''
                        CREATE TABLE IF NOT EXISTS deposits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id INTEGER,
                        deposit REAL,
                        date TEXT
                        )
                    ''')
            con.commit()
            data = c.execute('SELECT DISTINCT discord_id FROM deposits')
            ids = [row[0] for row in data.fetchall()]
        return ids

    def load_deposits(self, discordid: int) -> tuple:
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''
                        CREATE TABLE IF NOT EXISTS deposits (
                        id INTEGER PRIMARY KEY,
                        discord_id INTEGER,
                        deposit REAL,
                        date TEXT
                        )
                    ''')
            con.commit()
            data = c.execute('SELECT deposit, date FROM deposits WHERE discord_id = ?', (discordid,))
            rows = data.fetchall()
        return rows
    
    async def cog_command_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.respond("You don't have permission to use this command.", ephemeral=True)
        if isinstance(error, NotOwner):
            await ctx.respond("You are not my Owner.", ephemeral=True)

def curdir(filename: str):
    path = Path(sys.path[0], filename)
    return path

def setup(bot):
    bot.add_cog(ClanBank(bot))
    