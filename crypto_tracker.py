import time
import pprint as pp
from kucoin.user.user import UserData
from kucoin.trade.trade import TradeData
from kucoin.market.market import MarketData
import plotly.graph_objects as go
from collections import defaultdict
import pandas as pd
from utilities import *
import pickle
import json


user = UserData(key=API_KEY, secret=API_SECRET, passphrase=API_PASSWORD)
trade = TradeData(key=API_KEY, secret=API_SECRET, passphrase=API_PASSWORD)
market = MarketData(key=API_KEY, secret=API_SECRET, passphrase=API_PASSWORD)

def get_account_dict():
    account_list_raw = user.get_account_list()

def get_account_ledgers():
    '''
    This function will return a list of all transactions made in all of your accounts, beginning from the start date
    until today, in chronological order.
    :return: list
    '''
    ledger_history = []
    tmp_date = START_DATE

    while datetime.today().timestamp() > tmp_date.timestamp():
        tmp_date_millis = int(tmp_date.timestamp() * 1000)
        ledger = user.get_account_ledger(startAt=tmp_date_millis, pageSize=PAGE_SIZE)
        for page in range(1, ledger.get('totalPage') + 1):
            ledger = user.get_account_ledger(startAt=tmp_date_millis, pageSize=PAGE_SIZE, currentPage=page)
            if ledger.get('items'):
                ledger_history.append(ledger)
        tmp_date += timedelta(days=1)

    trans_list = []
    ids = []
    for ledger in ledger_history:
        for page in range(1, ledger.get('totalPage') + 1):
            for item in ledger['items']:
                trans_list.append(item)
                ids.append(item['id'])

    uniqueness_test = len(ids) == len(set(ids))
    print(f'Uniqueness test result is: {uniqueness_test}')
    trans_list.sort(key=lambda x: x.get('createdAt'))

    return trans_list

def get_balances(trans_list: list):
    '''
    This function will read a list of all the transactions made in all accounts, and will append a "balances" item to
    the dictionary of every transaction.
    :return: dict
    '''
    #
    balance_dict = defaultdict(lambda: [0, 0])  # balances of coins with key being timestamp and value being the dictionary of all the balances
    balance_time_dict = {}
    fund_dict = {}  # dict containing the transactions funding my trading account
    funds_usd = 0

    for item in trans_list:
        currency = item.get('currency')
        direction = item.get('direction')
        amount = float(item.get('amount'))
        timestamp = int(item.get('createdAt'))
        biz_type = item.get('bizType')

        balance_dict[currency][0] += (1 if direction == 'in' else -1) * amount

        if currency == 'USDT' and direction in ['in', 'out'] and biz_type == 'Exchange':
            symbol_pair = json.loads(item.get('context')).get('symbol')
            coin = symbol_pair.replace(currency, '').replace('-', '')
            balance_dict[coin][1] += (-1 if direction == 'in' else 1) * amount  # this is the amount that has been exchanged for the coin

        balance_time_dict[timestamp] = balance_dict.copy()  # todo this dictionary is getting overwritten with incorrect values (SAND was an example)

        if currency == 'DOGE' and direction in ['in', 'out'] and biz_type in ['Deposit', 'Withdraw']:  # DOGE is the coin I deposit and withdraw from kucoin with
            while True:
                try:
                    funds_usd += (1 if direction == 'in' else -1) * amount * float(market.get_kline(f'{currency}-USDT',
                                                startAt=int(timestamp / 1000), endAt=int(timestamp / 1000) + 180, kline_type='3min')[0][1])
                    time.sleep(0.2)
                except:
                    print(f'Getting rate limited at the fund dictionary step; sleeping for 5 seconds')
                    time.sleep(5)
                    continue
                fund_dict[timestamp] = funds_usd
                break

    return balance_time_dict, fund_dict

def get_balance_values(balance_dict: dict, fund_dict: dict):
    '''
    This function will map crypto balances to an arbitrary time. This function will be used to return a daily balance
    and worth of my accounts.
    :param balance_dict:
    :return:
    '''
    if not os.path.exists(PICKLE_FILEPATH):
        tmp_date = START_DATE
        total_dict = {}
        total_fund_dict = {}
        total_coin_fund_dict = {}
    else:
        total_dict, total_fund_dict, total_coin_fund_dict = load_pickle()
        tmp_date = list(total_dict.keys())[-1] + PLOT_STEP

    while datetime.today().timestamp() > tmp_date.timestamp():
        tmp_date_secs = int(tmp_date.timestamp())
        tmp_date_millis = int(tmp_date.timestamp() * 1000)
        #  find the day of the last transaction since the current day
        balance_day_diff_list = [(tmp_date_millis - day, day) for day in balance_dict.keys() if (tmp_date_millis - day) > 0]
        fund_diff_list = [(tmp_date_millis - day, day) for day in fund_dict.keys() if (tmp_date_millis - day) > 0]

        if balance_day_diff_list:
            balance_day = min(balance_day_diff_list, key=lambda x: x[0])[1]
            balance = balance_dict[balance_day]

        else:
            balance = {}

        if fund_diff_list:
            fund_day = min(fund_diff_list, key=lambda x: x[0])[1]
            fund = fund_dict[fund_day]
        else:
            fund = 0

        #  extract the price of the coins at the tmp_date using the balance of balance
        price_dict = {}
        coin_fund_dict = {}
        for currency in balance.keys():
            while True:
                try:
                    currency_worth = balance.get(currency, [0, 0])[0] * (float(market.get_kline(f'{currency}-USDT', startAt=tmp_date_secs,
                                                endAt=tmp_date_secs + 60, kline_type='1min')[0][1]) if currency != 'USDT' else 1)
                except Exception as e:
                    msg = e
                    time.sleep(12)
                    print(f'Getting account worth from {tmp_date.strftime("%d_%m_%Y")} Getting rate limited: {msg}')
                    continue
                price_dict[f'{currency}-USDT'] = currency_worth
                funded = balance.get(currency, [0, 0])[1]
                coin_fund_dict[currency] = [currency_worth, funded]
                break

        total_dict[tmp_date] = sum(price_dict.values())
        total_fund_dict[tmp_date] = fund
        total_coin_fund_dict[tmp_date] = coin_fund_dict
        tmp_date += PLOT_STEP

        print(f'Getting account worth from {tmp_date.strftime("%d_%m_%Y")}')

    return total_dict, total_fund_dict, total_coin_fund_dict

def reshape_dict(coin_fund_dict):
    ret_dict = {}
    for currency in coin_fund_dict[list(coin_fund_dict.keys())[-1]].keys():
        total_dict = dict([(key, val) for key, val in zip(list(coin_fund_dict.keys()), [coin_fund_dict.get(timestamp).get(currency, [0, 0])[0] for timestamp in coin_fund_dict.keys()])])
        fund_dict = dict([(key, val) for key, val in zip(list(coin_fund_dict.keys()), [coin_fund_dict.get(timestamp).get(currency, [0, 0])[1] for timestamp in coin_fund_dict.keys()])])

        ret_dict[currency] = [total_dict, fund_dict]

    return ret_dict

def plot(total_dict, total_fund_dict, title):
    # Create figure
    fig = go.Figure()

    total_y = list(total_dict.values())
    fund_y = list(total_fund_dict.values())
    profit = [int((100 * (total - fund) / fund) if fund else 0) for fund, total in zip(fund_y, total_y)]
    hovertext = [f'{int(total)} \n Profit: {percent}%' for total, percent in zip(total_y, profit)]

    fig.add_trace(
        go.Scatter(x=list(total_dict.keys()), y=total_y, name='Market Worth', hovertext=hovertext))

    fig.add_trace(
        go.Scatter(x=list(total_fund_dict.keys()), y=fund_y, name='Funds Invested'))

    # Set title
    fig.update_layout(title_text=title)

    # Add range slider
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    fig.show()

def save_pickle(input_object):
    try:
        with open(PICKLE_FILEPATH, 'wb') as f:
            pickle.dump(input_object, f)
    except Exception as e:
        print(f'Failed to save pickle file \n {e}')

def load_pickle():
    try:
        with open(PICKLE_FILEPATH, 'rb') as f:
            loaded_obj = pickle.load(f)
        return loaded_obj
    except:
        print(f'No pickle file found at path {PICKLE_FILEPATH}')


if __name__ == '__main__':
    trans_list = get_account_ledgers()
    balance_dict, fund_dict = get_balances(trans_list)
    worth_dict, total_fund_dict, coin_fund_dict = get_balance_values(balance_dict, fund_dict)
    save_pickle([worth_dict, total_fund_dict, coin_fund_dict])
    plot_dict = reshape_dict(coin_fund_dict)

    plot(worth_dict, total_fund_dict, title='Total portfolio worth vs. Time')
    for coin, (total, fund) in plot_dict.items():
        title = f'{coin} worth vs. Time'
        plot(total, fund, title=title)


    #  todo : Create multiple plots where I can see how much I am up or down on individual investments.


    #  todo: edit the script to output a list of how much you are up or down on various investments, and from different time periods + overall
    #  todo: add the feature where I can select a segment on the plot and I get shown the percentage difference between the start and end of the selection.


    # pp.pprint(test)