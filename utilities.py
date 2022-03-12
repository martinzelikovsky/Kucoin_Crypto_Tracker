from datetime import datetime, timedelta
import os
import time
from kucoin.user.user import UserData
from kucoin.trade.trade import TradeData
from kucoin.market.market import MarketData
import plotly.graph_objects as go
from collections import defaultdict
import pickle
import json
from copy import deepcopy
from tqdm import tqdm

#  Credentials
API_KEY = None
API_SECRET = None
API_PASSWORD = None

#  Utilities
START_DATE = datetime.strptime('01.01.2021 00:00:00,00', '%d.%m.%Y %H:%M:%S,%f')  # Enter correct start date
START_DATE_MILLIS = int(START_DATE.timestamp() * 1000)
PAGE_SIZE = 500  # number of entries per page in API response
PLOT_STEP = timedelta(days=1)  # resolution of profit/losses across time

PICKLE_FILEPATH = os.path.join(os.getcwd(), f'total_dict.pickle')  # account data is stored to reduce run time

if all([API_KEY, API_SECRET, API_PASSWORD, START_DATE]):
    print('Precheck completed successfully')
else:
    raise Exception('Enter API, and start date information in utilities.py')

user = UserData(key=API_KEY, secret=API_SECRET, passphrase=API_PASSWORD)
trade = TradeData(key=API_KEY, secret=API_SECRET, passphrase=API_PASSWORD)
market = MarketData(key=API_KEY, secret=API_SECRET, passphrase=API_PASSWORD)



