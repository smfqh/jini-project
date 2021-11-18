import os
import time
import sys
import pyupbit
import datetime
import schedule
import logging
import traceback
from decimal import Decimal
import math
import uuid
import requests
import jwt
from fbprophet import Prophet
import hashlib
from urllib.parse import urlencode

# Keys

server_url = 'https://api.upbit.com'


min_order_amt = 5000
buy_amt = 50000  
my_pect = 10

def start_second_dream():
    try: 
        
        except_items = ""

        while True:

            # 1. available amt
            available_amt = get_krwbal()['available_krw']

            # 2. my coin list
            my_items = get_accounts('Y','KRW')
            my_items_comma = chg_account_to_comma(my_items)
            tickers = get_ticker(my_items_comma)


            now = datetime.datetime.now()            
            start_time = get_start_time("KRW-BTC")
            end_time = start_time + datetime.timedelta(days=1) 


            if available_amt > buy_amt : 
                target_items = get_items('KRW', except_items)

                for target_item in target_items:
                    logging.info('Checking....[' + str(target_item['market']) + ']')
            
                    if start_time < now < end_time - datetime.timedelta(seconds=10):
                        current_price = get_current_price(target_item['market'])
                        print("current_price:" + str(current_price))
                        predict_price = get_predict_price(target_item['market'])
                        print("predict_price:" + str(predict_price))                

                        rev_pcnt = round((Decimal(str(predict_price)) - Decimal(str(current_price))) / Decimal(str(predict_price)) * 100 , 2)

                        if Decimal(str(rev_pcnt)) > Decimal(str(my_pect)):

                            logging.info('find item....[' + str(target_item['market']) + ']')
                            if Decimal(str(available_amt)) < Decimal(str(buy_amt)):
                                continue

                            if Decimal(str(buy_amt)) < Decimal(str(min_order_amt)):
                                continue

                            if str(target_item['market']) in my_items_comma :
                                for my_item in my_items:
                                    for ticker in tickers:
                                        if my_item['market'] == ticker['market'] and target_item['market'] == my_item['market']:
                                            rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(my_item['avg_buy_price']))) / Decimal(str(my_item['avg_buy_price']))) * 100, 2)

                                            logging.info('rev_pcnt! [' + str(rev_pcnt) + ']')

                                            if Decimal(str(rev_pcnt)) < Decimal(str(-2)):
                                                logging.info('buy start! [' + str(target_item['market']) + ']')
                                                rtn_buycoin_mp = buycoin_mp(target_item['market'], buy_amt)
                                                logging.info('buy end! [' + str(target_item['market']) + ']')
                                                logging.info(rtn_buycoin_mp)
                                            
                            else :
                                logging.info('buy start! [' + str(target_item['market']) + ']')
                                rtn_buycoin_mp = buycoin_mp(target_item['market'], buy_amt)
                                logging.info('buy end! [' + str(target_item['market']) + ']')
                                logging.info(rtn_buycoin_mp)

                    os.system('cat /dev/null > output.log') 

    except Exception:
        raise 

def get_start_time(ticker):
    """start time search!!!"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time


def get_current_price(ticker):
    """current price search"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]


def get_predict_price(ticker):
    try:

        """Prophet으로 당일 종가 가격 예측"""
        predicted_close_price = 0
        df = pyupbit.get_ohlcv(ticker, interval="minute60")
        df = df.reset_index()
        df['ds'] = df['index']
        df['y'] = df['close']
        data = df[['ds','y']]
        model = Prophet()
        model.fit(data)
        future = model.make_future_dataframe(periods=24, freq='H')
        forecast = model.predict(future)
        closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
        if len(closeDf) == 0:
            closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
        closeValue = closeDf['yhat'].values[0]
        predicted_close_price = closeValue

        return predicted_close_price

    except Exception:
        raise

def get_krwbal():
    try:
        # 잔고 리턴용
        rtn_balance = {}
        # fee
        fee_rate = 0.05
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
        res = send_request("GET", server_url + "/v1/accounts", "", headers)
        data = res.json()
        for dataFor in data:
            if (dataFor['currency']) == "KRW":
                krw_balance = math.floor(Decimal(str(dataFor['balance'])))
 
        if Decimal(str(krw_balance)) > Decimal(str(0)):
            fee = math.ceil(Decimal(str(krw_balance)) * (Decimal(str(fee_rate)) / Decimal(str(100))))
            available_krw = math.floor(Decimal(str(krw_balance)) - Decimal(str(fee)))
        else:
            fee = 0
            available_krw = 0
 
        rtn_balance['krw_balance'] = krw_balance
        rtn_balance['fee'] = fee
        rtn_balance['available_krw'] = available_krw
 
        return rtn_balance
 
    except Exception:
        raise

def get_items(market, except_item):
    try:
 
        rtn_list = []
        markets = market.split(',')
        except_items = except_item.split(',')
 
        url = "https://api.upbit.com/v1/market/all"
        querystring = {"isDetails": "false"}
        response = send_request("GET", url, querystring, "")
        data = response.json()
 
        for data_for in data:
            for market_for in markets:
                if data_for['market'].split('-')[0] == market_for:
                    rtn_list.append(data_for)
 
        for rtnlist_for in rtn_list[:]:
            for exceptItemFor in except_items:
                for marketFor in markets:
                    if rtnlist_for['market'] == marketFor + '-' + exceptItemFor:
                        rtn_list.remove(rtnlist_for)
 
        return rtn_list

    except Exception:
        raise    

def get_accounts(except_yn, market_code):
    try:
 
        rtn_data = []
 
        # 소액 제외 기준
        min_price = 5000
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/accounts", "", headers)
        account_data = res.json()
 
        for account_data_for in account_data:
 

            if except_yn == "Y" or except_yn == "y":
                if account_data_for['currency'] != "KRW" and Decimal(str(account_data_for['avg_buy_price'])) * (
                        Decimal(str(account_data_for['balance'])) + Decimal(
                        str(account_data_for['locked']))) >= Decimal(str(min_price)):
                    rtn_data.append(
                        {'market': market_code + '-' + account_data_for['currency'],
                         'balance': account_data_for['balance'],
                         'locked': account_data_for['locked'],
                         'avg_buy_price': account_data_for['avg_buy_price'],
                         'avg_buy_price_modified': account_data_for['avg_buy_price_modified']})
            else:
                if account_data_for['currency'] != "KRW" :
                    rtn_data.append(
                    {'market': market_code + '-' + account_data_for['currency'], 'balance': account_data_for['balance'],
                     'locked': account_data_for['locked'],
                     'avg_buy_price': account_data_for['avg_buy_price'],
                     'avg_buy_price_modified': account_data_for['avg_buy_price_modified']})
 
        return rtn_data

    except Exception:
        raise

def buycoin_mp(target_item, buy_amount):
    try:
 
        query = {
            'market': target_item,
            'side': 'bid',
            'price': buy_amount,
            'ord_type': 'price',
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        logging.info("")
        logging.info("----------------------------------------------")
        logging.info("buy end!")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    except Exception:
        raise

def get_ticker(target_itemlist):
    try:
 
        url = "https://api.upbit.com/v1/ticker"
 
        querystring = {"markets": target_itemlist}
        response = send_request("GET", url, querystring, "")
        rtn_data = response.json()
        return rtn_data
    except Exception:
        raise


def chg_account_to_comma(account_data):
    try:
        rtn_data = ""
        for account_data_for in account_data:
            if rtn_data == '':
                rtn_data = rtn_data + account_data_for['market']
            else:
                rtn_data = rtn_data + ',' + account_data_for['market']
        return rtn_data
    except Exception:
        raise


# Logging Level Setting
def set_loglevel(level):
    try:
        if level.upper() == "D":
            logging.basicConfig(
                format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]:%(message)s',
                datefmt='%Y/%m/%d %I:%M:%S %p',
                level=logging.DEBUG
            )
        elif level.upper() == "E":
            logging.basicConfig(
                format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]:%(message)s',
                datefmt='%Y/%m/%d %I:%M:%S %p',
                level=logging.ERROR
            )
        else:
            logging.basicConfig(
                format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]:%(message)s',
                datefmt='%Y/%m/%d %I:%M:%S %p',
                level=logging.INFO
            )

    except Exception:
        raise

def send_request(reqType, reqUrl, reqParam, reqHeader):
    try:
        err_sleep_time = 0.3
        while True:
            response = requests.request(reqType, reqUrl, params=reqParam, headers=reqHeader)
            if 'Remaining-Req' in response.headers:
                hearder_info = response.headers['Remaining-Req']
                start_idx = hearder_info.find("sec=")
                end_idx = len(hearder_info)
                remain_sec = hearder_info[int(start_idx):int(end_idx)].replace('sec=', '')
            else:
                logging.error("헤더 정보 이상")
                logging.error(response.headers)
                break

            if int(remain_sec) < 3:
                logging.debug("요청 가능회수 한도 도달! 남은횟수:" + str(remain_sec))
                time.sleep(err_sleep_time)

            if response.status_code == 200 or response.status_code == 201:
                break
            elif response.status_code == 429:
                logging.error("요청 가능회수 초과!:" + str(response.status_code))
                time.sleep(err_sleep_time)
            else:
                logging.error("기타 에러:" + str(response.status_code))
                logging.error(response.status_code)
                break

            logging.info("[restRequest] ...")
 
        return response
    except Exception:
        raise



# -----------------------------------------------------------------------------
# - Name : main
# - Desc : 메인
# -----------------------------------------------------------------------------
if __name__ == '__main__':
 
    # noinspection PyBroadException
    try:
 
        # 1. loglevel setting
        set_loglevel("E")
         # 매수 로직 시작
        start_second_dream()
        
 
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)
 
    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)
