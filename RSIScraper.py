import os
import sys
import traceback
import logging
import json
import requests 
import time
import yarl
import gc
import functools
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from pathlib import Path

logname = Path(sys.path[0], 'RSIScraper.log')

logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger()

class RSIScraper:
    class Organization:
        def __init__(self, organization_tag):
            self.__organization_tag = organization_tag
            self.URL = f'https://robertsspaceindustries.com/orgs/{self.__organization_tag}'
            self.__website = requests.get(self.URL)
            self.exists = True
            self.__webSoup = BeautifulSoup(self.__website.content, 'html.parser')
            if self.__website.status_code == 404:
                self.exists = False
                logger.error(f'Organization {self.__organization_tag} not found')
        #Attributes      
            self.members = self.Members(self.__organization_tag, self.exists)
            if self.exists:
                self.name, self.tag = self.fetch_organization_nameandtag()
            else:
                self.name, self.tag = 'Organization not found'

        def fetch_organization_nameandtag(self):
            org_str = self.__webSoup.find('div', {'class': 'page-wrapper'}).find('div', {'class': 'content-wrapper'}).find('h1').text.split('/')
            orgname = org_str[0].rstrip(' ')
            orgtag = org_str[1].lstrip(' ')
            return orgname, orgtag

        class Members:
            def __init__(self, organization_tag:str, parent_exists:bool):
                self.__organization_tag = organization_tag
                self.URL = f'https://robertsspaceindustries.com/orgs/{self.__organization_tag}/members'
                self.__website = requests.get(self.URL)
                self.__webSoup = BeautifulSoup(self.__website.content, 'html.parser')
                if parent_exists:
                    self.list = self.fetch_member_list()
                    self.amount = len(self.list)
                else:
                    self.list = []
                    self.amount = -1

            def fetch_member_list(self):
                try:
                    member_cards = self.__webSoup.find_all('li', {"class": lambda x: x and x.startswith('member-item js-member-item')})
                    names = []
                    for card in member_cards:
                        name = card.find('span', {"class": lambda x: x and x.startswith('trans-03s nick data')}).text.strip()
                        if name == '':
                            name = 'REDACTED'
                        names.append(name)
                    return names
                except:logger.error(traceback.format_exc())

    class User:
        def __init__(self, username):
            self.name = username
            self.URL = f'https://robertsspaceindustries.com/citizens/{self.name}'
            self.__website = requests.get(self.URL)    
            self.__webSoup = BeautifulSoup(self.__website.content, 'html.parser')
            self.exists = True
            if self.__website.status_code == 404:
                self.exists = False
                logger.error(f'User {self.name} not found')
        #Attributes
            self.organizations = self.Organizations(self.__webSoup, self.exists)
            self.accountage = self.AccountAge(self.__webSoup, self.exists)
            self.media = self.Media(self.__webSoup, self.exists)
            if not self.exists:
                self.name = 'User not found'

        class Organizations:
            def __init__(self, __webSoup:BeautifulSoup, parent_exists:bool):
                self.__webSoup = __webSoup
                self.__main_tag = 'None'
                self.__has_main =  False
                self.__main_rank = 'None'
                if parent_exists:
                    self.__main_tag, self.__has_main = self.fetch_main_tag()
                    if self.__has_main:
                        self.main = RSIScraper.Organization(self.__main_tag)
                        self.__main_rank = self.fetch_main_rank()
                else:
                    self.main = RSIScraper.Organization(self.__main_tag)
                self.main.rank = self.__main_rank

            def fetch_main_rank(self):
                try:
                    right_col = self.__webSoup.find('div', {"class": lambda x: x and x.startswith('visibility-')})
                    try:
                        entries = right_col.find('div', {'class': 'info'}).find_all('p', {'class': 'entry'})
                        for entry in entries:
                            try:
                                label = entry.find('span', {'class': 'label'})
                                if label.text.startswith('Organization rank'):
                                    org_rank = entry.find('strong', {'class': 'value'}).text.strip()
                                    break
                            except:
                                continue
                    except:
                        org_rank = right_col.find('div', {'class': 'empty'}).text.strip()
                except:
                    logger.error(traceback.format_exc())
                return org_rank

            def fetch_main_tag(self):
                try:
                    right_col = self.__webSoup.find('div', {"class": lambda x: x and x.startswith('visibility-')})
                    try:
                        entries = right_col.find('div', {'class': 'info'}).find_all('p', {'class': 'entry'})
                        for entry in entries:
                            try:
                                label = entry.find('span', {'class': 'label'})
                                if label.text.startswith('Spectrum Identification'):
                                    org_tag = entry.find('strong', {'class': 'value'}).text.strip()
                                    has_main = True
                                    break
                            except:
                                continue
                    except:
                        org_tag = right_col.find('div', {'class': 'empty'}).text.strip()
                        org_tag = 'None'
                        has_main = False
                except:
                    logger.error(traceback.format_exc())
                    org_tag = 'None'
                    has_main = False
                return org_tag, has_main

        class AccountAge:
            def __init__(self, __webSoup, parent_exists):
                self.__webSoup = __webSoup
                if parent_exists:
                    self.enlistment_date = self.fetch_enlistment_date()
                    self.relativedelta, self.str, self.dict = self.calc()
                else:
                    self.enlistment_date = self.fetch_enlistment_date()
                    self.relativedelta, self.str, self.dict = relativedelta(), 'None', {}

            def fetch_enlistment_date(self) -> str:
                """
                The function fetch_enlistment_date retrieves the enlistment date of a user.
                :return: The enlistment date is being returned.
                """
                try:
                    entries = self.__webSoup.find_all('p', {"class": "entry"})
                    for entry in entries:
                        labels = entry.find_all('span', {"class": "label"})
                        for label in labels:
                            if label.text.startswith('Enlisted'):
                                enlistment_date = entry.find('strong', {"class": "value"}).text.strip()
                                return enlistment_date
                except:logger.error(traceback.format_exc())

            def calc(self):
                enlisted_date = datetime.strptime(self.enlistment_date, '%b %d, %Y') if self.__webSoup is not None else None
                account_age = relativedelta(datetime.today(), enlisted_date) if self.__webSoup is not None else 'User not found'
                age_dict = {"years": account_age.years, "months": account_age.months, "days": account_age.days} if self.__webSoup is not None else 'User not found'
                age_str = '' 
                if self.__webSoup is not None:
                    age_str += f'{account_age.years} years ' if account_age.years >= 1 else ''
                    age_str += f'{account_age.months} months ' if account_age.months >= 1 else ''
                    age_str += f'{account_age.days} days' if account_age.days >= 1 else ''
                return account_age, age_str, age_dict

        class Media:
            def __init__(self, __webSoup, parent_exists):
                self.__webSoup = __webSoup
                self.profile_picture = self.fetch_profile_picture()

            def fetch_profile_picture(self) -> str:
                try:
                    if self.__webSoup is None:
                        return 'https://cdn.robertsspaceindustries.com/static/images/account/avatar_default_big.jpg'
                    profile = self.__webSoup.find('div', {'class': 'profile left-col'})
                    thumb_divs = profile.find_all('div', {'class': 'thumb'})
                    for div in thumb_divs:
                        img_url = div.find('img')['src']
                        if img_url is not None:
                            url_host = yarl.URL(img_url).raw_host
                            if url_host is None:
                                img_url = f'https://robertsspaceindustries.com{img_url}'
                            return img_url
                except:logger.error(traceback.format_exc())

#Org = RSIScraper.Organization('GERMANSTER')
#User = RSIScraper.User('Dnoxl')