import os
import sys
import traceback
import logging
import json
import requests 
import time
import yarl
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
        def __init__(self, organization):
            s = time.perf_counter()
            self.organization_name = organization
            self.URL = f'https://robertsspaceindustries.com/orgs/{self.organization_name}'
            self.__website = requests.get(self.URL)
            self.__webSoup = BeautifulSoup(self.__website.content, 'html.parser')
            if self.__website.status_code == 404:
                self.__webSoup = None
        #Attributes
            print(f'RSI Organization initialized in: {round(time.perf_counter()-s, 2)}s')

    class User:
        def __init__(self, username):
            s = time.perf_counter()
            self.user_name = username
            self.URL = f'https://robertsspaceindustries.com/citizens/{self.user_name}'
            self.__website = requests.get(self.URL)    
            self.__webSoup = BeautifulSoup(self.__website.content, 'html.parser')
            if self.__website.status_code == 404:
                self.__webSoup = None
        #Attributes
            self.main_organization = self.fetch_main_organization() if self.__webSoup is not None else 'User not found'
            self.enlistment_date = self.fetch_enlistment_date() if self.__webSoup is not None else 'User not found'
            self.account_age = self.calc_account_age()[0] if self.__webSoup is not None else 'User not found'
            self.account_age_str = self.calc_account_age()[1] if self.__webSoup is not None else 'User not found'
            self.account_age_dict = self.calc_account_age()[2] if self.__webSoup is not None else 'User not found'
            print(f'RSI User initialized in: {round(time.perf_counter()-s, 2)}s')

        def fetch_profile_picture(self):
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
        
        def fetch_main_organization(self):
            """
            The function fetch_main_organization attempts to find and return the name of the main
            organization of a user.
            :return: the name of the main organization.
            """
            try:
                org_info = self.__webSoup.find('div', {"class": lambda x: x and x.startswith('visibility-')})
                try:
                    org_name = org_info.find('a', {"class": "value"}).text.strip()
                except:
                    org_name = org_info.find('div', {'class': 'empty'}).text.strip()
                return org_name 
            except:logger.error(traceback.format_exc())

        def fetch_enlistment_date(self):
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

        def calc_account_age(self):
            enlisted_date = datetime.strptime(self.fetch_enlistment_date(), '%b %d, %Y') if self.__webSoup is not None else None
            account_age = relativedelta(datetime.today(), enlisted_date) if self.__webSoup is not None else 'User not found'
            age_dict = {"years": account_age.years, "months": account_age.months, "days": account_age.days} if self.__webSoup is not None else 'User not found'
            age_str = '' 
            if self.__webSoup is not None:
                age_str += f'{account_age.years} years ' if account_age.years >= 1 else ''
                age_str += f'{account_age.months} months ' if account_age.months >= 1 else ''
                age_str += f'{account_age.days} days' if account_age.days >= 1 else ''
            return account_age, age_str, age_dict