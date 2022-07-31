import os
import re
import copy
import time
import json

import tweepy
import requests

from datetime import datetime, timedelta
from dotenv import load_dotenv

# load environment variables

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_KEY_SECRET = os.getenv('API_KEY_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
SLEEPING_TIME = float(os.getenv('SLEEPING_TIME'))

# define some parameters

infinite_loop = True
bot_id = '1546134663990853634'
max_mentions = 10
file = '.last'
year_lower_bound = 2011
tweet_date_format = r'%d/%m/%Y'
api_date_format = r'%Y-%m-%dT%H:%M'
error_code_no_data = 502
energy_keys = ['wind', 'solar photovoltaic', 'thermal solar', 'hydro', 'nuclear', 'combined cycle', 'cogeneration', 'coal', 'other', 'total generation']

emojis = dict()

emojis['spain'] = '🇪🇸'
emojis['lightning'] = '⚡️'
emojis['red'] = '🔴'
emojis['orange'] = '🟠'
emojis['yellow'] = '🟡'
emojis['green'] = '🟢'
emojis['blue'] = '🔵'
emojis['purple'] = '🟣'
emojis['brown'] = '🟤'
emojis['black'] = '⚫️'
emojis['white'] = '⚪️'


class Energy:

    def __init__(self, description, value, units, emoji):

        self.description = description
        self.value = value
        self.units = units
        self.emoji = emoji


class Request:
    
    def __init__(self, text, geo_limit, geo_id):

        self.text = text.replace('\\', '/')

        self.geo_limit = geo_limit
        self.geo_id = geo_id
        self.geo_trunc = 'electric_system'

        self.pattern_dayly = '\d{1,2}/\d{1,2}/\d\d\d\d'
        self.pattern_monthly = '\d{1,2}/\d\d\d\d'
        self.pattern_anually = '\d\d\d\d'

        self.tweet_date = self._get_tweet_date()  # get date for tweet, None if no date was tweet
        # if no date is requested, set data from last available date in REE API
        self.tweet_date = self.tweet_date if self.tweet_date else get_last_available_date()
        self.tweet_format = self._get_tweet_format()
        self.time_trunc = self._get_time_trunc()
        self.date_obj = date_to_obj(self.tweet_date, self.tweet_format)
        self.start_date = obj_to_date(self.date_obj, api_date_format)
        self.end_date = self._get_end_date()
        
    def _get_tweet_date(self):

        if re.search(self.pattern_dayly, self.text):
            date = re.search(self.pattern_dayly, self.text)[0]
        elif re.search(self.pattern_monthly, self.text):
            date = re.search(self.pattern_monthly, self.text)[0]
        elif re.search(self.pattern_anually, self.text):
            date = re.search(self.pattern_anually, self.text)[0]
        else:
            date = None

        return date

    def _get_time_trunc(self):

        idx = self.tweet_date.count('/')

        return ['year', 'month', 'day'][idx]

    def _get_tweet_format(self):

        idx = self.tweet_date.count('/')

        return [r'%Y', r'%m/%Y', r'%d/%m/%Y'][idx]

    def _get_end_date(self):
        
        obj = self.date_obj

        if self.time_trunc == 'month':
            obj = obj.replace(day=28) + timedelta(days=4)  # the day 28 exists in every month. 4 days later, it's always next month
            obj = obj - timedelta(days=obj.day)  # subtracting the number of current day brings us back to last day of previous month
        elif self.time_trunc == 'year':
            obj = self.date_obj.replace(month=12, day=31)

        obj = obj.replace(hour=23, minute=59) # set to last minute

        return obj_to_date(obj, api_date_format)


class REE:

    def __init__(self, request):

        self.error = False
        self.error_code = 0
        self.error_description = ''
        self.request = request
        self.url = self._get_url()

        if self._is_lower_bound_error():
            self.error, self.error_code, self.error_description = self._get_lower_bound_error()
        
        if not self.error:
            
            self.json = self._get_json()
        
            if self._is_other_error():
                self.error, self.error_code, self.error_description = self._get_other_error()
            else:
                self.data = self._get_data()
                self.energies = self._get_energies()

    def __add__(self, other):

        result = copy.deepcopy(self)

        # add to result all energies that are in other but not in result
        for key in other.data:
            if key not in result.data:
                result.data[key] = {'value': float(), 'percentage': float()}

        # calculate result value
        for key in result.data:
            if key in other.data:  # skip energies that are in result but not in other
                result.data[key]['value'] += other.data[key]['value']

        # calculate result percentage
        for key in result.data:
            result.data[key]['percentage'] = 100 * result.data[key]['value'] / result.data['total generation']['value']

        result.energies = result._get_energies() # get energies again

        return result

    def __radd__(self, other):

        if other == 0:
            return self
        else:
            return self.__add__(other)

    def _is_lower_bound_error(self):

        year = self.request.date_obj.year

        return True if year < year_lower_bound else False

    def _is_other_error(self):

        return True if 'errors' in self.json else False

    def _get_lower_bound_error(self):

        error = True
        code = -1
        description = 'No existen datos antes del 2011'

        return error, code, description

    def _get_other_error(self):

        error = True
        code = self.json['errors'][0]['code']

        if code == error_code_no_data:
            description = 'No existen datos para ' + self.request.tweet_date
        else:
            description = self.json['errors'][0]['detail']

        return error, code, description

    def _get_url(self):

        return r'https://apidatos.ree.es/en/datos/generacion/estructura-generacion?' + \
               r'start_date=' + self.request.start_date + \
               r'&end_date=' + self.request.end_date + \
               r'&time_trunc=' + self.request.time_trunc.lower() + \
               r'&geo_trunc=' + self.request.geo_trunc + \
               r'&geo_limit=' + self.request.geo_limit + \
               r'&geo_ids=' + str(self.request.geo_id)

    def _get_json(self):

        # Request page content
        response = requests.get(self.url)

        # Decode the page content from bytes to string
        text = response.content.decode("utf-8")

        # Convert to json object
        return json.loads(text)

    # just for debug
    def _write_response(self, file):

        response = requests.get(self.url)
        
        with open(file, mode='wb') as d:
            d.write(response.content)

    def _get_data(self):

        data = dict()

        for included in self.json['included']:
                
            typ = included['type'].lower()
            value = included['attributes']['values'][0]  # this is an array but will always be one element in length (one day, one month or one year)

            data[typ] = {'value': value['value']/1000, 'percentage': 100*value['percentage']}  # GWh and %

        return data

    def _get_energies(self):

        my_units = '%'
        my_magnitude = 'percentage'
        others = 0
        energies = dict()
        edict = dict()
        
        edict['wind'] = {'description': 'Eólica', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'green'}
        edict['solar photovoltaic'] = {'description': 'Solar fotovoltaica', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'yellow'}
        edict['thermal solar'] = {'description': 'Solar térmica', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'brown'}
        edict['hydro'] = {'description': 'Hidráulica', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'blue'}
        edict['nuclear'] = {'description': 'Nuclear', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'orange'}
        edict['combined cycle'] = {'description': 'Ciclo combinado', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'red'}
        edict['cogeneration'] = {'description': 'Cogeneración', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'purple'}
        edict['coal'] = {'description': 'Carbón', 'magnitude': my_magnitude, 'units': my_units, 'emoji': 'black'}
        edict['total generation'] = {'description': 'Total', 'magnitude': 'value', 'units': ' GWh', 'emoji': 'lightning'}

        for key in self.data:
            
            if key in edict:
                description = edict[key]['description']
                magnitude = edict[key]['magnitude']
                units = edict[key]['units']
                emoji = emojis[edict[key]['emoji']]
                value = self.data[key][magnitude]
                energies[key] = {'description': description, 'value': value, 'units': units, 'emoji': emoji}
            else:
                # now for all 'other' energies
                others += self.data[key][my_magnitude]

        energies['other'] = {'description': 'Otras', 'value': others, 'units': '%', 'emoji': emojis['white']}

        return energies

    def get_tweet(self):

        if not self.error:

            text = f'Generación del {self.request.tweet_date} en {emojis["spain"]}\n\n'

            for key in energy_keys:
                if key in self.energies:
                    text += f'{self.energies[key]["emoji"]} {self.energies[key]["description"]}: {self.energies[key]["value"]:.1f}{self.energies[key]["units"]}\n'

        else:
            text = self.error_description

        return text


def write_last_tweet_id(file, id):

    with open(file, 'w') as f:
        f.write(str(id))

def read_last_tweet_id(file):

    with open(file, 'r') as f:
        return int(f.read())

def date_to_obj(date, date_format, delta_days=0):
    
    return datetime.strptime(date, date_format) + timedelta(days=delta_days)

def obj_to_date(obj, date_format, delta_days=0):
    
    return (obj + timedelta(days=delta_days)).strftime(date_format)

def get_last_available_date():

    geo_limit = 'peninsular'
    geo_id = 8741

    date = obj_to_date(datetime.now(), tweet_date_format)
    request = Request(date, geo_limit, geo_id)
    ree = REE(request)

    while ree.error_code == error_code_no_data:
        
        obj = date_to_obj(date, tweet_date_format, delta_days=-1)
        date = obj_to_date(obj, tweet_date_format)
        request = Request(date, geo_limit, geo_id)
        ree = REE(request)

    return date

def get_ree_and_request(text):

    geo_limits = ['peninsular',  'canarias', 'baleares', 'ceuta', 'melilla',]
    geo_ids = [8741, 8742, 8743, 8744, 8745]

    request = Request(text, geo_limits[0], geo_ids[0])
    ree_national = REE(request)

    for geo_limit, geo_id in zip(geo_limits[1:], geo_ids[1:]):

        request.geo_limit = geo_limit
        request.geo_id = geo_id
        ree = REE(request)

        if ree.error:
            return ree_national, request

        ree_national += REE(request)

    return ree_national, request


if __name__ == '__main__':

    while True:

        last_tweet_id = read_last_tweet_id(file) if os.path.isfile(file) else 0
        print(last_tweet_id)

        try:
   
            # authenticate client
            client = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET,
                                   access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
            
            # get bot mentions
            tweets = client.get_users_mentions(id=bot_id, max_results=max_mentions, since_id=last_tweet_id, user_auth=True)

        except Exception as error:

            tweets = list()
            print('Error finding mentions')
            print('Error is ' + str(error))

        if tweets and tweets.data:

            for tweet in tweets.data:

                text = ''

                try:

                    # print(tweet.text, tweet.id)
                    ree, request = get_ree_and_request(tweet.text)
                    text = ree.get_tweet()
                    # print(text)

                    # post tweet
                    client.create_tweet(text=text, in_reply_to_tweet_id=tweet.id)

                    if tweet.id > last_tweet_id:

                        last_tweet_id = tweet.id
                        write_last_tweet_id(file, tweet.id)

                    print(f'Tweet in response to tweet id {tweet.id} with request date {request.start_date} at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

                except Exception as error:

                    print(f'Error sending tweet, its length is {len(text)}')
                    print('Error is ' + str(error))

        # put to sleep

        if infinite_loop:
            time.sleep(SLEEPING_TIME)
        else:
            break
