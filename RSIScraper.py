import sys
import traceback
import logging
import aiohttp
import time
import asyncio
import html
import json
import re
from playwright.async_api import async_playwright
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from pathlib import Path
from selectolax.parser import HTMLParser

logname = Path(sys.path[0], 'RSIScraper.log')

logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger()

#constans
u_notfound = 'User not found'



class RSIScraper:
    class Information:
        def __init__(self, cache_duration=1):
            self.releaseurl = "https://robertsspaceindustries.com/roadmap/release-view"
            self.shipsurl = "https://robertsspaceindustries.com/pledge/ships"
            self.s = time.perf_counter()
            self.cache_duration = cache_duration*60**2 
            self.cache_duration = 0
            self.browser = None

            #FilePaths
            self.__releaseview_path = Path(sys.path[0], 'ReleaseView.json')

            #Selectors
            self.__banner_selector = 'li.banner-accept-button[id="allow-all"]'

        async def initialize(self):
            async with async_playwright() as p:
                if __name__ == '__main__':
                    if not disable_headless:
                        headless = True
                    else:
                        headless = False if sys.platform == 'win32' else True     
                else:
                    headless = True
                self.browser = await p.chromium.launch_persistent_context(user_data_dir=Path(sys.path[0], 'persistent_storage'), headless=headless)
                #self.releases = await self.fetch_releaseview(self.releaseurl)
                self.ships = await self.fetch_shiplist(self.shipsurl)
                await self.browser.close()

        async def fetch_releaseview(self, url):
                try:
                    with open(self.__releaseview_path, 'r') as f:
                        j = json.load(f)
                    cached_time = float(j['cached_time'])
                    if time.time() - cached_time < self.cache_duration:
                        return j
                except Exception:pass
                releases = {}
                versions = []
                page = await self.browser.new_page()
                await page.set_viewport_size({'width':1900, 'height':1060})
                await page.goto(url, wait_until='networkidle')
                banner = await page.query_selector(self.__banner_selector)
                if banner is not None:
                    await banner.click()
                button = await page.query_selector('button.Text-sc-461421-0.fmvgwk.Button-nt30ep-0.kYIlHp')
                if button is not None:
                    await page.click('button.Text-sc-461421-0.fmvgwk.Button-nt30ep-0.kYIlHp')
                await page.click('span.TogglePreviousReleases__Wrapper-yixp65-0')
                await asyncio.sleep(.25)
                await page.click('div.Button__Label-sc-1i76va4-0')
                await asyncio.sleep(.25)
                html = HTMLParser(await page.content())
                await page.close()
                releasewrappers = html.css('section.Release__Wrapper-sc-1y9ya50-0')
                for wrap in releasewrappers:
                    categories = wrap.css('section.Category__Wrapper-sc-3z36kz-0')
                    version = wrap.css_first('h2.Text-sc-461421-0.ReleaseHeader__ReleaseHeaderName-xqp955-1').text()
                    versions.append(version)
                    release = wrap.css_first('p.Text-sc-461421-0.ReleaseHeader__ReleaseHeaderStatus-xqp955-2').text().split(',', 1)
                    releases[version] = {'status': release[0], 'date': release[1].lstrip()}
                    for category in categories:
                        cat_title = category.css_first('h2.Text-sc-461421-0.Category__CategoryName-sc-3z36kz-4').text()
                        entry_count = category.css_first('h3.Text-sc-461421-0.Category__CardCount-sc-3z36kz-5').text()
                        releases[version][cat_title] = {'amount':entry_count, 'entries':[]}
                        sub_categories = category.css('section.Card__Wrapper-a2fcbm-0')
                        for sub_category in sub_categories:
                            sub_cat_title = sub_category.css_first('h3.Text-sc-461421-0').text()
                            sub_cat_text = sub_category.css_first('p.Text-sc-461421-0').text()
                            status = sub_category.css_first('span.Text-sc-461421-0').text()
                            link = f"https://robertsspaceindustries.com{sub_category.css_first('a.Card__StyledNavLink-a2fcbm-2').attrs['href']}"
                            releases[version][cat_title]['entries'].append({sub_cat_title:{'status':status, 'link':link, 'text':sub_cat_text}})
                tmp_releases = {}
                tmp_releases['cached_time'] = time.time()
                for v in sorted(versions, key=lambda version: tuple(map(int, version.split('.')))):
                    tmp_releases[v] = releases[v]
                releases = tmp_releases
                with open(self.__releaseview_path, 'w+') as f:
                    f.write(json.dumps(releases, indent=4))
                print(f'Operation took {round(time.perf_counter()-self.s, 2)}s')
                return releases
        
        async def fetch_shiplist(self, url):
                with open(self.__releaseview_path, 'r') as f:
                    j = json.load(f)
                cached_time = float(j['cached_time'])
                if time.time() - cached_time < self.cache_duration:
                    return j
                ships = {}
                page = await self.browser.new_page()
                await page.goto(url, wait_until='networkidle')
                banner = await page.query_selector(self.__banner_selector)
                if banner is not None:
                    await page.click('li.banner-accept-button[id="allow-selected"]')
                heights = [await page.evaluate('document.body.scrollHeight')]
                while True:
                    await page.mouse.wheel(0, 500)
                    time.sleep(.1)
                    height = await page.evaluate('document.body.scrollHeight')
                    if len(heights) >= 10:
                        heights.pop(0)
                        if height == sum(heights)/len(heights):
                            break
                    heights.append(height)
                html = HTMLParser(await page.content())
                await page.close()
                print(f'List took {round(time.perf_counter()-self.s, 2)}s')
                ship_items = html.css('li.ship-item')
                for i, item in enumerate(ship_items):
                    name = item.css_first('span.name.trans-02s').text()
                    link = item.css_first('a.filet').attrs['href']                    
                    status, price = await self.fetch_shipdata(url=f'https://robertsspaceindustries.com{link}')
                    print(f'{name}: {i+1}/{len(ship_items)} done, price: {price}')
                    ships[name] = {'link':f'https://robertsspaceindustries.com{link}', "status":status, "price":price}
                ships = dict(sorted(ships.items(), key=lambda x: x[0].lower()))
                ships['cached_time'] = time.time()
                print(len(ships))  
                with open(Path(sys.path[0], 'ShipList.json'), 'w+') as f:
                    f.write(json.dumps(ships, indent=4))
                print(f'Operation took {round(time.perf_counter()-self.s, 2)}s')
                return ships

        async def fetch_shipdata(self, url):
            try:
                page = await self.browser.new_page()
                await page.goto(url, wait_until='networkidle')
                '''
                try:
                    page.wait_for_selector('div.RSIStoreTheme.StoreWidget')
                except Exception:
                    print('No store widget found')
                    page.close()
                    status, price = self.fetch_shipdata(url=url)
                '''
                await asyncio.sleep(.25)
                banner = await page.query_selector(self.__banner_selector)
                if banner is not None:
                    await page.click('li.banner-accept-button[id="allow-selected"]')
                country_sel = page.locator('a.js-countryselector-list')
                if country_sel:
                    if await country_sel.locator('span').text_content() != 'United States':
                        await page.keyboard.press('End')
                        await country_sel.locator('div.arrow').click()
                        await page.wait_for_selector('li.js-option.option[rel="236"]')
                        await country_sel.locator('ul.body').locator('li.js-option[rel="236"]').click() 
                        await asyncio.sleep(.25)
                        await page.goto(url, wait_until='load')
                        await asyncio.sleep(1)
                html = HTMLParser(await page.content())                   
                status = html.css_first('div.prod-status').text().strip()
                _buying = html.css_first('a.holobtn.add-to-cart')
                price = 'Not available'               
                if _buying:
                    buy_menu = html.css_first('section.wcontent[id="buying-options"]')
                    buy_opt = buy_menu.css_first('div.buying-options-content')
                    buy_opts = buy_menu.css('div.row')
                    if buy_opt and buy_opt.css_first('div.type').css_first('span').text().split('–')[1].strip() == 'Standalone Ship':
                        price = buy_opt.css_first('strong.final-price').text().split(' ')[0] if not None else 'Not Available'
                    else:
                        if buy_opts:
                            for opt in buy_opts:
                                standalone_query = str(opt.css_first('div.type').css_first('span').text()).split('–')[1].strip()
                                if standalone_query and standalone_query == 'Standalone Ship':
                                    price = opt.css_first('strong.final-price').text().split(' ')[0] if not None else 'Not Available'
            except Exception:
                traceback.print_exc()
                print(url)
                await asyncio.sleep(1)
                await page.close()
                status, price = await self.fetch_shipdata(url=url)
            await page.close()
            return status, price

    class Organization:
        '''Call Organization.init() after creating an instance to obtain the HTML asynchronously'''
        def __init__(self, organization_tag):
            self.__organization_tag = organization_tag
            self.URL = f'https://robertsspaceindustries.com/orgs/{self.__organization_tag}'
            self.exists = True
            self.__status_code = None
            self.__html_text = None
            self.__html = None

        async def initialize(self):
            await self.fetch_html()
            self.members = self.Members(self.__organization_tag, self.exists)
            await self.members.initialize()
            if self.exists:
                self.name, self.tag = await self.fetch_organization_nameandtag()
            else:
                self.name, self.tag = 'Organization not found', 'Organization not found'

        async def fetch_html(self):
            async with aiohttp.ClientSession() as s:
                async with s.post(self.URL) as r:
                    self.__status_code = r.status
                    self.__html_text = await r.read()
            self.__html = HTMLParser(self.__html_text)
            if self.__status_code == 404:
                self.exists = False
                logger.warning(f'Organization {self.__organization_tag} not found')

        async def fetch_organization_nameandtag(self):
            org_str = self.__html.css_first('div.page-wrapper').css_first('div.content-wrapper').css_first('h1').text().split('/')
            orgname = org_str[0].rstrip(' ')
            orgtag = org_str[1].lstrip(' ')
            return orgname, orgtag

        class Members:
            def __init__(self, organization_tag:str, parent_exists:bool):
                self.__parent_exists = parent_exists
                self.__organization_tag = organization_tag
                self.dict = {}
                self.list = []
                self.amount = -1
                self.redacted_count = -1
                self.hidden_count = -1
                self.__html = None                     

            async def initialize(self):
                if self.__parent_exists:      
                    html_text = await self.fetch_html()
                    self.__html = HTMLParser(html_text)
                    self.dict, self.redacted_count, self.hidden_count = await self.fetch_members()
                    self.list = [key for key in self.dict.keys()]
                    self.amount = len(self.dict)+self.redacted_count+self.hidden_count      

            async def fetch_html(self):
                html_text = ""
                url = "https://robertsspaceindustries.com/api/orgs/getOrgMembers"
                headers = {
                            "authority": "robertsspaceindustries.com",
                            "accept": "*/*",
                            "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                            "content-type": "application/json",
                            "cookie": "Rsi-Token=5e8c02c45b79dc666b61b8f2252a9de4; Rsi-XSRF=YaZGZQ%3A%2FTfcdZLiZvJjgxSDw3XKFg%3APUNah0cqOaG7%2FySqt1CK0w%3A1699130732915; CookieConsent={stamp:%27HQsxLWb9HHhNnTZazTPSDPFCmWACZrED89LcCnPLCvz9VOMbZmaJMQ==%27%2Cnecessary:true%2Cpreferences:true%2Cstatistics:true%2Cmarketing:true%2Cmethod:%27explicit%27%2Cver:1%2Cutc:1699128936327%2Cregion:%27de%27}; moment_timezone=Europe%2FBerlin; _gcl_au=1.1.1824133565.1699128937; _ga=GA1.2.930138824.1699128937; _gid=GA1.2.478126376.1699128937",
                            "origin": "https://robertsspaceindustries.com",
                            "referer": f"https://robertsspaceindustries.com/orgs/{self.__organization_tag}/members",
                            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                            "sec-ch-ua-mobile": "?0",
                            "sec-ch-ua-platform": '"Windows"',
                            "sec-fetch-dest": "empty",
                            "sec-fetch-mode": "cors",
                            "sec-fetch-site": "same-origin",
                            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                            "x-requested-with": "XMLHttpRequest",
                            "x-rsi-token": "5e8c02c45b79dc666b61b8f2252a9de4"
                        }
                async with aiohttp.ClientSession() as s:
                    for i in range(1, 99999):
                        time.sleep(.3)
                        data = {
                            "symbol": f"{self.__organization_tag}",
                            "search": "",
                            "page": i,
                            "page-size": 32
                        }
                        async with s.post(url=url, headers=headers, json=data) as r:
                            rj = await r.json()
                        if rj['data']:
                            if rj['data']['html'] == '' or rj['data']['html'] == ' ':
                                break
                        else:
                            i -= 1
                            continue
                        try:
                            html_text += html.unescape(rj['data']['html'])
                        except Exception as e:
                            print(e, rj)
                            i -= 1
                return html_text
            
            async def fetch_members(self):
                try:
                    member_cards = self.__html.css('li.member-item.js-member-item')
                    redacted_cards = [card for card in member_cards if 'org-visibility-R' in card.attrs['class']]
                    hidden_cards = [card for card in member_cards if 'org-visibility-H' in card.attrs['class']]
                    member_dict = {}
                    for card in member_cards:
                        name = card.css_first('span.trans-03s.nick').text().strip()
                        if name != '':
                            rank_name = card.css_first('span.rank').text().strip()
                            rank_tier = int(int(card.css_first('span.stars').attrs['style'].split(':')[1].rstrip('%;'))/20)
                            member_dict[name] = rank_name, rank_tier
                    member_dict = dict(sorted(member_dict.items(), key=lambda item: item[0].lower()))
                    return member_dict, len(redacted_cards), len(hidden_cards)
                except Exception:
                    logger.error(traceback.format_exc())
                    return {}, 0, 0
  
    class User:
        def __init__(self, username):
            self.name = username
            self.URL = f'https://robertsspaceindustries.com/citizens/{username}'
            self.__html = None
            self.exists = True
        #Attributes
            self.organizations = None
            self.accountage = None            

        async def initialize(self):
            await self.fetch_html()
            self.organizations = self.Organizations(self.__html, self.exists)
            self.accountage = self.AccountAge(self.__html, self.exists)
            await self.organizations.initialize()
            await self.accountage.initialize()

        async def fetch_html(self):
            async with aiohttp.ClientSession() as s:
                async with s.post(self.URL) as r:
                    self.__status_code = r.status
                    self.__html_text = await r.read()
            self.__html = HTMLParser(self.__html_text)   
            if self.__status_code == 404:
                self.exists = False
                self.name = u_notfound
            else:
                self.name = self.__html.css_first('div.profile.left-col').css_first('div.info').css_first('strong.value').text().strip()

        class Organizations:
            def __init__(self, __html:HTMLParser, parent_exists:bool):
                self.__parent_exists = parent_exists
                self.__html = __html
                self.__main_tag = 'NO MAIN ORG'
                self.__has_main =  False
                self.__main_rank = self.__main_tag
                self.__main_rank_tier = self.__main_tag
                self.main = None

            async def initialize(self):
                if self.__parent_exists:
                    self.__main_tag, self.__has_main = await self.fetch_main_tag()
                    if self.__has_main:
                        self.__main_rank, self.__main_rank_tier = await self.fetch_main_rank()
                        self.main = RSIScraper.Organization(self.__main_tag)
                        await self.main.initialize()
                        self.main.rank = self.__main_rank
                        self.main.rank_tier = self.__main_rank_tier
                    else:
                        self.main = RSIScraper.Organization(self.__main_tag)
                        await self.main.initialize()

            async def fetch_main_rank(self):
                try:
                    right_col = self.__html.css_first('div.main-org.right-col')
                    try:
                        entries = right_col.css_first('div.info').css('p.entry')
                        for entry in entries:
                            try:
                                label = entry.css_first('span.label')
                                if label.text().strip().startswith('Organization rank'):
                                    org_rank = entry.css_first('strong.value').text().strip()
                                    break
                            except Exception:
                                continue
                        try:
                            rank_tier = len(right_col.css_first('div.ranking').css('span.active'))
                        except Exception:
                            logger.warning(traceback.format_exc())
                    except Exception:
                        logger.warning(traceback.format_exc())
                        org_rank = right_col.css_first('div.empty').text().strip()
                except Exception:
                    logger.error(traceback.format_exc())
                return org_rank, rank_tier

            async def fetch_main_tag(self):
                try:
                    right_col = self.__html.css_first('div.main-org.right-col')
                    try:
                        entries = right_col.css_first('div.info').css('p.entry')
                        for entry in entries:
                            try:
                                label = entry.css_first('span.label')
                                if label.text().strip().startswith('Spectrum Identification'):
                                    org_tag = entry.css_first('strong.value').text().strip()
                                    has_main = True
                                    break
                            except Exception:
                                continue
                    except Exception:
                        org_tag = 'ORG NOT FOUND'
                        has_main = False
                except Exception:
                    logger.error(traceback.format_exc())
                    org_tag = 'None'
                    has_main = False
                return org_tag, has_main

        class AccountAge:
            def __init__(self, __html:HTMLParser, parent_exists):
                self.__html = __html
                self.__parent_exists = parent_exists
                self.relativedelta, self.str, self.dict = relativedelta(), 'None', {}

            async def initialize(self):
                self.enlistment_date = await self.fetch_enlistment_date()
                if self.__parent_exists:
                    self.relativedelta, self.str, self.dict = await self.calc()

            async def fetch_enlistment_date(self) -> str:
                """
                The function fetch_enlistment_date retrieves the enlistment date of a user.
                :return: The enlistment date is being returned.
                """
                try:
                    entries = self.__html.css('p.entry')
                    for entry in entries:
                        labels = entry.css('span.label')
                        for label in labels:
                            if label.text().strip().startswith('Enlisted'):
                                enlistment_date = entry.css_first('strong.value').text().strip()
                                return enlistment_date
                except Exception:logger.error(traceback.format_exc())

            async def calc(self):
                enlisted_date = datetime.strptime(self.enlistment_date, '%b %d, %Y') if self.__html is not None else None
                account_age = relativedelta(datetime.today(), enlisted_date) if self.__html is not None else u_notfound
                age_dict = {"years": account_age.years, "months": account_age.months, "days": account_age.days} if self.__html is not None else u_notfound
                age_str = '' 
                if self.__html is not None:
                    age_str += f'{account_age.years} years ' if account_age.years >= 1 else ''
                    age_str += f'{account_age.months} months ' if account_age.months >= 1 else ''
                    age_str += f'{account_age.days} days' if account_age.days >= 1 else ''
                return account_age, age_str, age_dict

if __name__ == '__main__':
    s = time.perf_counter()
    async def org():
        org = RSIScraper.Organization('banutc')
        await org.initialize()
        print(org.name, org.members.list, org.members.amount)

    async def user():
        user = RSIScraper.User('Wolfrae')
        await user.initialize()
        print(user.accountage.str)

    async def relview():
        relview = RSIScraper.Information()
        await relview.initialize()

    async def main():
        pass
        await relview()
        #await org()
        #await user()
    
    global disable_headless
    disable_headless = True
    asyncio.run(main())
    print(f'Operations took {round(time.perf_counter()-s, 2)}s')