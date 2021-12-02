import time
import sys
import pyupbit
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
import datetime
import numpy as np


# Keys
access_key = "obxBT66Cx8fJsnww9TAfJwMKUx443RBiElaZRq1b"
secret_key = "wKUSQ8GaxDDC1BNcPWrNBjYQIP7ncEyv07j4TXTV"
server_url = 'https://api.upbit.com'

min_order_amt = 5000
fees = 0.0005
K = 0.5

buy_amt = 'M'  
my_pect = 7


def start_second_dream():
    try: 
        set_loglevel("I")
        
        # except_items = "MANA,SAND"
        global buy_amt
        except_items = ""

        while True:

            # 1. available amt
            available_amt = get_krwbal()['available_krw']

            target_items = get_items('KRW', except_items)

            now = datetime.datetime.now()
            start_time = get_start_time("KRW-BTC")
            end_time = start_time + datetime.timedelta(days=1)

            if buy_amt == 'M':
                buy_amt = available_amt

            logging.info('------------------------------------------------------')
            logging.info('- 가용금액:' + str(available_amt))
            logging.info('- 제외종목:' + str(except_items))            
            logging.info('------------------------------------------------------')


            if start_time < now < end_time - datetime.timedelta(minutes=10):

                if Decimal(str(available_amt))  >=  Decimal(str(buy_amt)) and Decimal(str(available_amt))  > Decimal(str(min_order_amt)) : 

                    for target_item in target_items:

                        current_price = get_current_price(target_item['market'])
                        predict_price = get_predict_price(target_item['market'])
                        rev_pcnt = round((Decimal(str(predict_price)) - Decimal(str(current_price))) / Decimal(str(predict_price)) * 100 , 2)

                        df = pyupbit.get_ohlcv(target_item['market'], count = 2, interval = "day")
                        targetPrice = get_targetPrice(df, get_best_K(target_item['market'], fees))   
                        pre_pcnt = round((Decimal(str(predict_price)) - Decimal(str(targetPrice))) / Decimal(str(predict_price)) * 100 , 2)

 
                        if Decimal(str(rev_pcnt)) > Decimal(str(my_pect))  and Decimal(str(targetPrice)) <= Decimal(str(current_price)) : 

                            logging.info('------------------------------------------------------')
                            logging.info('- 종목:' + str(target_item['market']))
                            logging.info('- 현재가:' + str(current_price))
                            logging.info('- 종가 예상:' + str(predict_price))
                            logging.info('- 수익율 예상:' + str(rev_pcnt))
                            logging.info('- 목표가 :' + str(targetPrice))
                            logging.info('- 예상 수익율 :' + str(pre_pcnt))
                            logging.info('------------------------------------------------------')   


                            if Decimal(str(available_amt)) < Decimal(str(buy_amt)):
                                continue
                           
                            if Decimal(str(buy_amt)) < Decimal(str(min_order_amt)):
                                continue

                            buycoin_mp(target_item['market'], buy_amt)

                            # ------------------------------------------------------------------
                            # 매수 완료 종목은 매수 대상에서 제외
                            # ------------------------------------------------------------------
                            if except_items.strip():
                                except_items = except_items + ',' + target_item['market'].split('-')[1]
                            else:
                                except_items = target_item['market'].split('-')[1]



            else:
                # ------------------------------------------------------------------
                # 보유 종목조회
                # ------------------------------------------------------------------
                target_items = get_accounts('Y', 'KRW')

                if len(target_items) > 0 :
                    # -----------------------------------------------------------------
                    # 보유 종목별 진행
                    # -----------------------------------------------------------------
                    for target_item in target_items:
                        
                        sellcoin_mp(target_item['market'], 'Y')

                        time.sleep(2)                        

                    except_items = ""

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

def get_targetPrice(df, K) :
    try:    
        range = df['high'][-2] - df['low'][-2]
        return df['open'][-1] + range * K
    except Exception:
        raise


def get_best_K(coin, fees) :
    try:    

        df = pyupbit.get_ohlcv(coin, interval = "day", count = 21)
        max_crr = 0
        best_K = 0.5
        for k in np.arange(0.0, 1.0, 0.1) :
            crr = get_crr(df, fees, k)
            if crr > max_crr :
                max_crr = crr
                best_K = k
        return best_K

    except Exception:
        raise


def get_crr(df, fees, K) :
    try:    

        df['range'] = df['high'].shift(1) - df['low'].shift(1)
        df['targetPrice'] = df['open'] + df['range'] * K
        df['drr'] = np.where(df['high'] > df['targetPrice'], (df['close'] / (1 + fees)) / (df['targetPrice'] * (1 + fees)) , 1)
        return df['drr'].cumprod()[-2]

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

def sellcoin_mp(target_item, cancel_yn):
    try:
 
        if cancel_yn == 'Y':
            cancel_order(target_item, "SELL")
 
        cur_balance = get_balance(target_item)
 
        query = {
            'market': target_item,
            'side': 'ask',
            'volume': cur_balance,
            'ord_type': 'market',
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
        logging.info("시장가 매도 완료!")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    except Exception:
        raise

def get_order(target_item):
    try:
        query = {
            'market': target_item,
            'state': 'wait',
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
 
        res = send_request("GET", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
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


def cancel_order(target_item, side):
    try:
 
        order_data = get_order(target_item)
 
        for order_data_for in order_data:
 
            if side == "BUY" or side == "buy":
                if order_data_for['side'] == "ask":
                    order_data.remove(order_data_for)
            elif side == "SELL" or side == "sell":
                if order_data_for['side'] == "bid":
                    order_data.remove(order_data_for)
 
        if len(order_data) > 0:
 
            for order_data_for in order_data:
                cancel_order_uuid(order_data_for['uuid'])
 
    except Exception:
        raise

def cancel_order_uuid(order_uuid):
    try:
 
        query = {
            'uuid': order_uuid,
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
 
        res = send_request("DELETE", server_url + "/v1/order", query, headers)
        rtn_data = res.json()
 
        return rtn_data
 

    except Exception:
        raise

def get_balance(target_item):
    try:
 
        # 주문가능 잔고 리턴용
        rtn_balance = 0
 
        # 최대 재시도 횟수
        max_cnt = 0
 
        # 잔고가 조회 될 때까지 반복
        while True:
 
            # 조회 회수 증가
            max_cnt = max_cnt + 1
 
            payload = {
                'access_key': access_key,
                'nonce': str(uuid.uuid4()),
            }
 
            jwt_token = jwt.encode(payload, secret_key)
            authorize_token = 'Bearer {}'.format(jwt_token)
            headers = {"Authorization": authorize_token}
 
            res = send_request("GET", server_url + "/v1/accounts", "", headers)
            my_asset = res.json()
 
            # 해당 종목에 대한 잔고 조회
            # 잔고는 마켓에 상관없이 전체 잔고가 조회됨
            for myasset_for in my_asset:
                if myasset_for['currency'] == target_item.split('-')[1]:
                    rtn_balance = myasset_for['balance']
 
            # 잔고가 0 이상일때까지 반복
            if Decimal(str(rtn_balance)) > Decimal(str(0)):
                break
 
            # 최대 100회 수행
            if max_cnt > 100:
                break
 
            logging.info("[주문가능 잔고 리턴용] 요청 재처리중...")
 
        return rtn_balance
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
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
