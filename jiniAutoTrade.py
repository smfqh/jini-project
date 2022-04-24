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
import hashlib
from urllib.parse import urlencode

# Keys
access_key = "obxBT66Cx8fJsnww9TAfJwMKUx443RBiElaZRq1b"
secret_key = "wKUSQ8GaxDDC1BNcPWrNBjYQIP7ncEyv07j4TXTV"
server_url = 'https://api.upbit.com'

min_order_amt = 5000

# 종목별 매수 금액 설정(일정 금액 직접 입력)
item_buy_amt = 50000

# 추가매수/매도 기준 및 추매 금액
add_purchase = -2.5
add_sell = 2
add_buy = item_buy_amt/2
item_max_buy = item_buy_amt*10

# 매수/매도 제외항목
# ex ) sell_except_item = ["XRP"]  
sell_except_item = []  

# 손절 기준
loss_cut = -20

# 올어라운드 매수 기준
all_around_amt = 2000000

upbit = pyupbit.Upbit(access_key, secret_key)

# ------------------------------------------------------------------
# start second dream
# ------------------------------------------------------------------
def start_second_dream():
    try: 
        # ------------------------------------------------------------------
        # log 기준
        # ------------------------------------------------------------------
        set_loglevel("I")

        while True:

            # ------------------------------------------------------------------
            # 잔고 조회
            # ------------------------------------------------------------------
            available_amt = get_krwbal()['available_krw']

            # ------------------------------------------------------------------
            # 보유 종목조회
            # ------------------------------------------------------------------
            my_items = get_accounts('Y', 'KRW')   
            my_items_comma = chg_account_to_comma(my_items)
            tickers = get_ticker(my_items_comma)  


            tot_buy = 0
            tot_present_val = 0
            income_val = 0
            tot_pcnt = 0

            # -----------------------------------------------------------------
            # 올어라운드 매수 시작
            # -----------------------------------------------------------------
            if len(my_items) < 60  and available_amt > all_around_amt:

                # 전 종목 리스트 조회
                item_list = get_items('KRW', my_items_comma)
                        
                logging.info(len(item_list))
                logging.info(item_list)
       
                # 종목별 매수 금액 설정(KRW잔고 이용)
                # item_buy_amt = math.floor(available_amt / len(item_list))

                logging.info(item_buy_amt)
                logging.info(available_amt)
                logging.info(my_items_comma)


                # 종목별 처리
                for item_list_for in item_list:
        
                    logging.info('종목코드:' + item_list_for['market'])
                    # 시장가 매수
                    buycoin_mp(item_list_for['market'], item_buy_amt)
        
                logging.info('전 종목 매수 완료')                      
        
            # -----------------------------------------------------------------
            # 보유 종목별 진행
            # -----------------------------------------------------------------
            if len(my_items) > 0 :

                for my_item in my_items:
                    
                    for ticker in tickers:
                 
                        if my_item['market'] == ticker['market']:

                            # -----------------------------------------------------------------
                            # 보유 종목별 진행
                            # item_buy : 종목별 총구매 금액
                            # item_present : 종목별 현재 금액
                            # item_income : 종목별 손익 계산
                            # tot_buy : 총보유종목 구매금액 합
                            # tot_present_val : 총보유종목 현재금액 합
                            # -----------------------------------------------------------------
                            item_buy = (Decimal(str(my_item['avg_buy_price']))) * Decimal(str((my_item['balance'])))  
                            item_present = (Decimal(str(ticker['trade_price']))) * Decimal(str((my_item['balance'])))
                            item_income = (item_present - item_buy ) / item_buy * 100

                            tot_buy = tot_buy + item_buy    
                            tot_present_val = tot_present_val + item_present


                            current_price = get_current_price(my_item['market'])


                            logging.info("*********************************************************")
                            logging.info("1. 보유 종목  : " + str(my_item['market']))
                            logging.info("2. 수익율(%)  : " + str(round(item_income,2)) + " % ")
                            logging.info("4. 매수 금액  : " + str("{0:,}".format(round(item_buy,0))))
                            logging.info("3. 현재 가격  : " + str("{0:,}".format(current_price)))
                            logging.info("*********************************************************")                              

                            # -----------------------------------------------------------------
                            # 손절 로직(매도 제외항목 손절기준 적용)
                            # -----------------------------------------------------------------                            
                            if my_item['market'].split('-')[1] not in sell_except_item : 

                                if round(item_income) < loss_cut :
                                    logging.info('시장가 손절 시작! [' + str(my_item['market']) + ']')
                                    rtn_sellcoin_mp = sellcoin_mp(my_item['market'], 'Y')
                                    logging.info('시장가 손절 종료! [' + str(my_item['market']) + ']')
                                    logging.info(rtn_sellcoin_mp)
                                    logging.info('------------------------------------------------------') 


                            # -----------------------------------------------------------------
                            # 추매 또는 매도 
                            # -----------------------------------------------------------------                              
                            if round(item_income, 2) < add_purchase: 

                                if Decimal(str(available_amt)) < Decimal(str(add_buy)):
                                    continue
                            
                                if Decimal(str(add_buy)) < Decimal(str(min_order_amt)):
                                    continue

                                if Decimal(str(item_buy)) > Decimal(str(item_max_buy)):
                                    continue

                                logging.info('시장가 추매 시작! [' + str(my_item['market']) + ']')
                                logging.info('현재 보유 금액! [' + str(item_buy) + ']')                                
                                rtn_buycoin_mp = buycoin_mp(my_item['market'], add_buy)
                                logging.info('시장가 추매 종료! [' + str(my_item['market']) + ']')
                                logging.info(rtn_buycoin_mp)

                            if round(item_income, 2) >= add_sell: 

                                if my_item['market'].split('-')[1] not in sell_except_item : 

                                    if item_buy < item_buy_amt +10000:
                                        
                                        logging.info('시장가 매도 시작! [' + str(my_item['market']) + ']')
                                        rtn_sellcoin_mp = sellcoin_mp(my_item['market'], 'Y')
                                        logging.info('시장가 매도 종료! [' + str(my_item['market']) + ']')
                                        logging.info(rtn_sellcoin_mp)
                                        logging.info('------------------------------------------------------') 

                                    else :

                                        if Decimal(str(item_buy)) < Decimal(str(min_order_amt)):
                                            continue

                                        sell_coin = round(Decimal(get_balance(my_item['market']))/item_buy*item_buy_amt,2)
                                        logging.info('코인! [' + str(sell_coin) + ']')
                                        logging.info('시장가 매도 시작! [' + str(my_item['market']) + ']')
                                        upbit.sell_market_order(my_item['market'], sell_coin)
                                        logging.info('시장가 매도 종료! [' + str(my_item['market']) + ']')
                                        logging.info('------------------------------------------------------') 
                                            
                            time.sleep(1)

                income_val = tot_present_val - tot_buy
                tot_pcnt = (tot_present_val - tot_buy ) / tot_buy * 100      

            logging.info("*********************************************************")
            logging.info("1. 총매수금액 : " + str("{0:,}".format(round(tot_buy))))
            logging.info("2. 가용 금액  : " + str("{0:,}".format(available_amt)))
            logging.info("3. 현재 금액  : " + str("{0:,}".format(round(tot_present_val))))
            logging.info("4. 손익 금액  : " + str("{0:,}".format(round(income_val))))
            logging.info("5. 수익율(%)  : " + str(round(tot_pcnt,2)) + " % ")
            logging.info("*********************************************************")                         


    except Exception:
        raise 


def get_current_price(ticker):
    """current price search"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]



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
                    if rtnlist_for['market'] == exceptItemFor:
                        rtn_list.remove(rtnlist_for)
 
        return rtn_list

    except Exception:
        raise  

def get_accounts(except_yn, market_code):
    try:
 
        rtn_data = []
 
        # 소액 제외 기준
        # min_price = 5000
        min_price = 1000
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
               
        # rtn_data = "KRW-BTC,KRW-ETH,KRW-SOL,KRW-STRK,KRW-ETC,KRW-GRS,KRW-BCH,KRW-AXS,KRW-LTC,KRW-WAVES,KRW-BTG"
        rtn_data = "KRW-BTT"
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
