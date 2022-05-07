from datetime import datetime, timedelta
import os
import time
import plotly.graph_objects as go
from collections import defaultdict
import pickle
import json
from copy import deepcopy
from tqdm import tqdm
import requests
import base64
import hmac
import hashlib
from urllib.parse import urljoin, urlencode

#  Credentials
API_KEY = None
API_SECRET = None
API_PASSWORD = None

#  Utilities
START_DATE = datetime.strptime('01.11.2021 00:00:00,00', '%d.%m.%Y %H:%M:%S,%f')  # Enter correct start date
START_DATE_MILLIS = int(START_DATE.timestamp() * 1000)
PAGE_SIZE = 500  # number of entries per page in API response
PLOT_STEP = timedelta(days=1)  # resolution of profit/losses across time

PICKLE_FILEPATH = os.path.join(os.getcwd(), f'total_dict_feature.pickle')  # account data is stored to reduce run time

# Kucoin API Information
URL = 'https://api.kucoin.com'
LEDGER_POLL_PERIOD = 3/18
KLINE_POLL_PERIOD = 0.5

if all([API_KEY, API_SECRET, API_PASSWORD, START_DATE]):
    print('Precheck completed successfully')
else:
    raise Exception('Enter API, and start date information in utilities.py')

def get_account_ledgers_request(start_time=int(time.time() * 1000), current_page=1):
    now = int(time.time() * 1000)
    params = {'startAt': start_time, 'currentPage': current_page, 'pageSize': 500}
    uri = f'/api/v1/accounts/ledgers?{urlencode(params)}'
    str_to_sign = f'{now}GET{uri}'
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode('utf-8'), API_PASSWORD.encode('utf-8'), hashlib.sha256).digest())
    headers = {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": API_KEY,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2"
    }
    url = urljoin(URL, uri)
    response = requests.request('get', url, headers=headers)
    return response

def get_kline_request(symbol_pair: str, start_time: int, end_time: int, kline_type='1min'):
    now = int(time.time() * 1000)
    params = {'symbol': symbol_pair, 'startAt': start_time, 'endAt': end_time, 'type': kline_type}
    uri = f'/api/v1/market/candles?{urlencode(params)}'
    str_to_sign = f'{now}GET{uri}'
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode('utf-8'), API_PASSWORD.encode('utf-8'), hashlib.sha256).digest())
    headers = {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": API_KEY,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2"
    }
    url = urljoin(URL, uri)
    response = requests.request('get', url, headers=headers)
    return response

