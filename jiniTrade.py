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
import numpy as np
import datetime
import warnings
import pandas as pd


warnings.filterwarnings("ignore", category=FutureWarning)
#logging.getLogger('fbprophet').setLevel(logging.WARNING) 

# Keys
access_key = ""
secret_key = ""
server_url = 'https://api.upbit.com'



# 최소요청 금액
min_order_amt = 5000

# 매도수익율
sell_pcnt = 1.0
buy_pcnt = 2.0

# 추가매수 
add_purchase1 = -7.0
add_purchase2 = -10.0

# 예측 수익율
my_pcnt = 3.0

# 수수료
fees = 0.05

#변동성 K값
K = 0.5

# 매수/매도 제외항목
# ex ) sell_except_item = ["XRP"]  
sell_except_item = []
buy_except_item = ["BTT","SSX"]

upbit = pyupbit.Upbit(access_key , secret_key)

#초기상태 : jini를 실행시키기 위한 플래그
jini = True
all_around = False

#구매조건(초기 금액) 
all_around_amt = 10000

#평균구매전략
avg_amt = 10000

#구매조건 코인수(수량 이하면 비보유 전체 매수)
all_around_count = 50

#대기시간
waiting = 1


def start_second_dream():

    try:
        # ------------------------------------------------------------------
        # log 기준 및 세팅 확인
        # ------------------------------------------------------------------
        set_loglevel("I")

        global access_key
        global secret_key
        global jini
        global all_around
        global upbit
        global all_around
        global all_around_amt
        global avg_amt
        global sell_pcnt


        while True:

            # ------------------------------------------------------------------
            # 평균구매 적략 및 매도금액 설정
            # ------------------------------------------------------------------
            avg_amt = 10000
            #today = datetime.datetime.today()
            #avg_day = int(today.day)

            #if avg_day <= 7 :
                #avg_day = 7

            avg_day = 15
            
            # ------------------------------------------------------------------
            #jini만 실행 시
            # ------------------------------------------------------------------
            #jini = True

            if jini:

                access_key = ""
                secret_key = ""

                upbit = pyupbit.Upbit(access_key , secret_key)

                # ------------------------------------------------------------------
                # 잔고 조회
                # ------------------------------------------------------------------
                available_amt = get_krwbal()['available_krw']

                # ------------------------------------------------------------------
                # 보유 종목조회
                # ------------------------------------------------------------------
                my_items = get_accounts('Y', 'KRW')

                if len(my_items)> 0 :
                    my_items_comma = chg_account_to_comma(my_items)
                    tickers = get_ticker(my_items_comma)
                else :
                    my_items_comma = ''

                # ------------------------------------------------------------------
                # 비 보유 종목 조회 
                # ------------------------------------------------------------------
                target_items = get_items('KRW', my_items_comma)
                target_items_comma = chg_account_to_comma(target_items)
                target_tickers = get_ticker(target_items_comma)

                all_around = True
                jini = False

            else :

                access_key = ""
                secret_key = ""

                upbit = pyupbit.Upbit(access_key , secret_key)

                # ------------------------------------------------------------------
                # 잔고 조회
                # ------------------------------------------------------------------
                available_amt = get_krwbal()['available_krw']

                # ------------------------------------------------------------------
                # 보유 종목조회
                # ------------------------------------------------------------------
                my_items = get_accounts('Y', 'KRW')

                if len(my_items)> 0 :
                    my_items_comma = chg_account_to_comma(my_items)
                    tickers = get_ticker(my_items_comma)
                else :
                    my_items_comma = ''

                # ------------------------------------------------------------------
                # 비 보유 종목 조회 
                # ------------------------------------------------------------------
                target_items = get_items('KRW', my_items_comma)
                target_items_comma = chg_account_to_comma(target_items)
                target_tickers = get_ticker(target_items_comma)

                all_around = True
                jini = True

            # -----------------------------------------------------------------
            # 보유 종목별 진행
            # item_buy_amt : 종목별 구매 금액
            # item_present : 종목별 현재 금액
            # tot_present_val : 총보유종목 현재금액 합
            # -----------------------------------------------------------------

            tot_present_val = 0
            item_present = 0

            if len(my_items) > 0 :
                for my_item in my_items:
                    for ticker in tickers:
                        if my_item['market'] == ticker['market']:
                            item_present = (Decimal(str(ticker['trade_price']))) * Decimal(str((my_item['balance'])))
                            tot_present_val = tot_present_val + item_present

            rev1 = 0

            current_price = get_current_price("KRW-ETH")
            eth_ticker = get_ticker("KRW-ETH")
            prev_close_price = eth_ticker[0]['prev_closing_price']
            eth_rev= round((Decimal(str(current_price)) - Decimal(str(prev_close_price))) / Decimal(str(prev_close_price)) * 100 , 2)

            current_price = get_current_price("KRW-BTC")
            btc_ticker = get_ticker("KRW-BTC")
            prev_close_price = btc_ticker[0]['prev_closing_price']
            btc_rev= round((Decimal(str(current_price)) - Decimal(str(prev_close_price))) / Decimal(str(prev_close_price)) * 100 , 2)

            if eth_rev >= -0.5 :
                rev1 = rev1 + 1
            else:
                rev1 = rev1 - 1

            if btc_rev >= -0.5 :
                rev1 = rev1 + 1
            else:
                rev1 = rev1 - 1


            if all_around :
                avg_amt  = int((tot_present_val+ available_amt)/100000) * 100000 / 100
                all_around_amt = avg_amt * 10


            #1회 최소구매 금액설정            
            if all_around_amt < 10000:
                all_around_amt = 10000

            if not jini:
                logging.info("*********************************************************")
                logging.info("                      jini's coin                        ")
            else:
                logging.info("*********************************************************")
                logging.info("                       lee's coin                        ")

            if all_around :
                logging.info("                      AI모드 : OFF                       ")

                if rev1 > 0 :
                    logging.info("\033[1;91m                    구매/추매모드("+ str(rev1) +") \033[0m")
                else:
                    logging.info("\033[1;94m                      매도 모드(" + str(rev1) + ") \033[0m")

            logging.info("0.  현재 자산          : " + str("{0:,}".format(round(tot_present_val+available_amt,0)))+" 원")
            logging.info("1.  총 보유종목수      : " + str(len(my_items))+"개")
            logging.info("2.  비 보유종목수      : " + str(len(target_items))+"개")
            logging.info("3.  최소매도수익율     : " + str(sell_pcnt)+"%")
            logging.info("4.  추가 매수율        : " + str(add_purchase1)+"% ~ " + str(add_purchase2)+"%")
            logging.info("5.  현 평가총액        : " + str("{0:,}".format(round(tot_present_val,0)))+" 원")

            if all_around :
                logging.info("6.  평균구매금액       : " + str("{0:,}".format(round(avg_amt,0)))+" 원")
                logging.info("7.  최대추매금액       : " + str("{0:,}".format(round(all_around_amt,0)))+" 원")
                logging.info("8.  가 용 금 액        : " + str("{0:,}".format(round(available_amt,0)))+" 원")

            logging.info("*********************************************************")

            buy_count = 0

            if all_around:
                #갯수제한
                if len(my_items) < all_around_count and available_amt >= avg_amt and rev1 > 0 : 

                #if available_amt >= avg_amt and rev1 > 0 :

                    # 종목별 처리
                    for target_items_for in target_items:

                        available_amt = get_krwbal()['available_krw']

                        if Decimal(str(available_amt)) < Decimal(str(avg_amt)):
                            continue

                        for target_ticker in target_tickers:

                            if target_items_for['market'] == target_ticker['market']:

                                if target_items_for['market'].split('-')[1] not in buy_except_item :

                                    current_price = get_current_price(target_ticker['market'])
                                    prev_close_price = target_ticker['prev_closing_price']
                                    current_income = (Decimal(str(current_price))-Decimal(str(prev_close_price))) / Decimal(str(prev_close_price)) * 100
                                    average_price =  get_average_price(target_ticker['market'], avg_day)

                                    if current_price > 10000 or current_price < 1:
                                        continue

                                    if not jini:
                                        logging.info("*********************************************************")
                                        logging.info("                      jini's Time                        ")
                                    else:
                                        logging.info("*********************************************************")
                                        logging.info("                       lee's Time                        ")

                                    logging.info("1. 대상 종목         : " + str(target_items_for['market']))
                                    logging.info("2. 현 재 가          : " + str(current_price) + " 원")
                                    logging.info("3. 기준일 평균가     : " + str(average_price) + " 원")                                   
                                    logging.info("4. 현재수익율(%)     : " + str("{0:,}".format(round(current_income,2))) + "% ")

                                    if Decimal(str(average_price)) >=  Decimal(str(current_price)):

                                        logging.info("                   기준("+str(avg_day)+")일 평균가 이하 !!!                ")

                                        if current_income < -sell_pcnt:

                                            logging.info("                    현재 -"+str(sell_pcnt)+ " 이하" )

                                            logging.info('  시장가 구매 시작! [' + str(target_items_for['market']) + ']')
                                            buycoin_mp(target_items_for['market'], avg_amt)
                                            logging.info('  시장가 구매 종료! [' + str(target_items_for['market']) + ']')
                                            # 시장가 매수
                                            buy_count += 1

                                    logging.info("*********************************************************")

                                time.sleep(waiting)

                    logging.info("*********************************************************")
                    logging.info("")
                    logging.info(" 구매 종목수    : " + str(buy_count)+"개")
                    logging.info("               전 종목 매수 완료                         ")
                    logging.info("*********************************************************")

                    logging.info("")
                    logging.info("")
                    logging.info("")

            # -----------------------------------------------------------------
            # 보유 종목별 진행
            # -----------------------------------------------------------------
            if  len(my_items) > 0 :

                for my_item in my_items:

                    for ticker in tickers:

                        if my_item['market'] == ticker['market']:

                            # -----------------------------------------------------------------
                            # 보유 종목별 진행
                            # item_buy : 종목별 총구매 금액
                            # item_present : 종목별 현재 금액
                            # item_income : 종목별 손익 계산
                            # -----------------------------------------------------------------
                            item_buy = (Decimal(str(my_item['avg_buy_price']))) * Decimal(str((my_item['balance'])))
                            item_present = (Decimal(str(ticker['trade_price']))) * Decimal(str((my_item['balance'])))
                            item_income = (Decimal(str(item_present)) - Decimal(str(item_buy))) / Decimal(str(item_buy)) * 100
                            current_price = get_current_price(my_item['market'])
                            prev_close_price = ticker['prev_closing_price']   
                            current_income = (Decimal(str(current_price))-Decimal(str(prev_close_price))) / Decimal(str(prev_close_price)) * 100
                            avg_buy  = Decimal(str(my_item['avg_buy_price']))
                            #기준일 이내 최저가
                            lowest_price = get_lowest_price(my_item['market'], avg_day)
                        
                            rsi_val = False
                            mfi_val = False
                            ocl_val = False
                            # --------------------------------------------------------------
                            # 종목별 보조지표를 조회
                            # 1. 조회 기준 : 일캔들, 최근 5개 지표 조회
                            # --------------------------------------------------------------
                            indicators_data = get_indicators(my_item['market'], 'D', 200, 5)

                            # --------------------------------------------------------------
                            # 최근 30일 이내에 신규 상장하여 보조 지표를 구하기 어려운 건은 제외
                            # --------------------------------------------------------------
                            if len(indicators_data) < 5:
                                logging.info("*********************************************************")                                
                                logging.info('- 캔들 데이터 부족으로 매수 대상에서 제외....[' + str(my_item['market']) + ']')
                                logging.info("*********************************************************")
                                continue

                            # --------------------------------------------------------------
                            # 매도 로직
                            # 1. RSI : 2일전 > 70초과, 3일전 < 2일전, 1일전 < 2일전, 현재 < 1일전
                            # 2. MFI : 2일전 > 80초과, 3일전 < 2일전, 1일전 < 2일전, 현재 < 1일전
                            # 3. MACD(OCL) : 3일전 > 0, 2일전 > 0, 1일전 > 0, 3일전 < 2일전, 1일전 < 2일전, 현재 < 1일전
                            # --------------------------------------------------------------

                            # --------------------------------------------------------------
                            # RSI : 2일전 > 70초과, 3일전 < 2일전, 1일전 < 2일전, 현재 < 1일전
                            # indicators_data[0][0]['RSI'] : 현재
                            # indicators_data[0][1]['RSI'] : 1일전
                            # indicators_data[0][2]['RSI'] : 2일전
                            # indicators_data[0][3]['RSI'] : 3일전
                            # --------------------------------------------------------------
                            if (Decimal(str(indicators_data[0][0]['RSI'])) < Decimal(str(indicators_data[0][1]['RSI']))
                                    and Decimal(str(indicators_data[0][1]['RSI'])) < Decimal(str(indicators_data[0][2]['RSI']))
                                    and Decimal(str(indicators_data[0][3]['RSI'])) < Decimal(str(indicators_data[0][2]['RSI']))
                                    and Decimal(str(indicators_data[0][2]['RSI'])) > Decimal(str(70))):
                                rsi_val = True

                            # --------------------------------------------------------------
                            # MFI : 2일전 > 80초과, 3일전 < 2일전, 1일전 < 2일전, 현재 < 1일전
                            # indicators_data[1][0]['MFI'] : 현재
                            # indicators_data[1][1]['MFI'] : 1일전
                            # indicators_data[1][2]['MFI'] : 2일전
                            # indicators_data[1][3]['MFI'] : 3일전
                            # --------------------------------------------------------------
                            if (Decimal(str(indicators_data[1][0]['MFI'])) < Decimal(str(indicators_data[1][1]['MFI']))
                                    and Decimal(str(indicators_data[1][1]['MFI'])) < Decimal(str(indicators_data[1][2]['MFI']))
                                    and Decimal(str(indicators_data[1][3]['MFI'])) < Decimal(str(indicators_data[1][2]['MFI']))
                                    and Decimal(str(indicators_data[1][2]['MFI'])) > Decimal(str(80))):
                                mfi_val = True

                            # --------------------------------------------------------------
                            # MACD(OCL) : 3일전 > 0, 2일전 > 0, 1일전 > 0, 3일전 < 2일전, 1일전 < 2일전, 현재 < 1일전
                            # indicators_data[2][0]['OCL'] : 현재
                            # indicators_data[2][1]['OCL'] : 1일전
                            # indicators_data[2][2]['OCL'] : 2일전
                            # indicators_data[2][3]['OCL'] : 3일전
                            # --------------------------------------------------------------
                            if (Decimal(str(indicators_data[2][0]['OCL'])) < Decimal(str(indicators_data[2][1]['OCL']))
                                    and Decimal(str(indicators_data[2][1]['OCL'])) < Decimal(str(indicators_data[2][2]['OCL']))
                                    and Decimal(str(indicators_data[2][3]['OCL'])) < Decimal(str(indicators_data[2][2]['OCL']))
                                    and Decimal(str(indicators_data[2][1]['OCL'])) > Decimal(str(0))
                                    and Decimal(str(indicators_data[2][2]['OCL'])) > Decimal(str(0))
                                    and Decimal(str(indicators_data[2][3]['OCL'])) > Decimal(str(0))):
                                ocl_val = True


                            available_amt = get_krwbal()['available_krw']

                            if not jini:
                                logging.info("*********************************************************")
                                logging.info("                      jini's coin                        ")
                            else:
                                logging.info("*********************************************************")
                                logging.info("                       lee's coin                        ")

                            if all_around :

                                if rev1 > 0 :
                                    logging.info("\033[1;91m                    구매/추매모드("+ str(rev1) +") \033[0m")
                                else:
                                    logging.info("\033[1;94m                      매도 모드(" + str(rev1) + ") \033[0m")

                            logging.info("- 현재 자산        : " + str("{0:,}".format(round(tot_present_val+available_amt,0)))+" 원")
                            logging.info("- 가용 금액        : " + str("{0:,}".format(round(available_amt,0)))+" 원")

                            logging.info("- 상대강도지수(RSI): " + str(round(indicators_data[0][0]['RSI'],2)))
                            logging.info("- MFI              : " + str(round(indicators_data[1][0]['MFI'],2)))
                            logging.info("- 이동평균(MACD)   : " + str(round(indicators_data[2][0]['OCL'],2)))

                            logging.info("- 보유 종목        : " + str(my_item['market']))
                            
                            if item_income >= 0 :
                                logging.info("\033[1;91m- 내수익율(%)      : " + str(round(item_income,2)) + " %\033[0m")
                            else:
                                logging.info("\033[1;94m- 내수익율(%)      : " + str(round(item_income,2)) + " %\033[0m")

                            logging.info("- 현재수익율(%)    : " + str("{0:,}".format(round(current_income,2))) + " % ")
                            logging.info("- 총매수 금액      : " + str("{0:,}".format(round(item_buy)))+" 원")
                            logging.info("- 비트코인수익률 : " +str(btc_rev)+ " %,  이더리움수익율 : " +str(eth_rev)+" %")                            
                            #logging.info("- 현재 가격        : " + str("{0:,}".format(current_price,2))+ " 원")                                

                            buy_cost = avg_amt

                            if lowest_price >  current_price:
                                logging.info("                       최저가 당첨 !!!                        ")
                                buy_cost = item_buy * 1.5

                            logging.info("*********************************************************")

                            # -----------------------------------------------------------------
                            # 추매 
                            # -----------------------------------------------------------------                              
                            # rev ( 0 : 기본 , 1 이상 추매 , 2 이상 구매, -2 이하 매도)
                            if all_around:

                                if current_income < 0 and rev1 > 0:

                                    if  Decimal(str(round(item_income,2))) <=  Decimal(str(add_purchase1)):

                                        if Decimal(str(round(item_income,2))) >=  Decimal(str(add_purchase2)):

                                            if  Decimal(str(available_amt))  >=  Decimal(str(buy_cost)):

                                                if Decimal(str(item_buy)) <= Decimal(str(all_around_amt)):

                                                    if Decimal(str(all_around_amt)) < Decimal(str(min_order_amt)):
                                                        continue

                                                    logging.info('시장가 추매 시작! [' + str(my_item['market']) + ']')
                                                    rtn_buycoin_mp = buycoin_mp(my_item['market'], buy_cost)
                                                    logging.info('시장가 추매 종료! [' + str(my_item['market']) + ']')
                                                    logging.info("*********************************************************")


                            # -----------------------------------------------------------------
                            # 매도 
                            # -----------------------------------------------------------------  
                            # rev ( 0 : 기본 , 1 이상 추매 , 2 이상 구매, -2 이하 매도)
                            # rev1 이더리움 비트코인이 마이너스
                            # 예측 금액이 - 인경우

                            if all_around:

                                if round(item_income, 2) >  sell_pcnt :
                                    logging.info("*********************************************************")
                                    logging.info('시장가 매도 시작! [' + str(my_item['market']) + ']')
                                    rtn_sellcoin_mp = sellcoin_mp(my_item['market'], 'Y')
                                    logging.info('시장가 매도 종료! [' + str(my_item['market']) + ']')
                                    logging.info("*********************************************************")

                    time.sleep(waiting)

    except Exception:
        raise

def get_start_time(ticker):
    """start time search!!!"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time


def get_current_price(ticker):
    """current price search"""
    #print(pyupbit.get_orderbook(ticker=ticker)["orderbook_units"])
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]


def get_lowest_price(coin, days):
    try:
        # 코인의 최근 일정 기간의 가격 데이터 가져오기
        df = pyupbit.get_ohlcv(coin, count=days)

        # 최저가 찾기
        lowest_price = df['low'].min()

        return lowest_price

    except Exception as e:
        print(f"Error occurred: {e}")
        raise


def get_average_price(coin, days):
    try:
        # 코인의 최근 일정 기간의 가격 데이터 가져오기
        df = pyupbit.get_ohlcv(coin, count=days)

        # 최저가와 최고가 계산
        lowest_price = df['low'].min()
        highest_price = df['high'].max()

        # 평균가 계산
        average_price = (lowest_price + highest_price) / 2

        return average_price

    except Exception as e:
        print(f"Error occurred: {e}")
        raise

def get_targetPrice(df, K) :
    try:
        range = df['high'][-2] - df['low'][-2]
        return df['open'][-1] + range * K
    except Exception:
        raise


def get_best_K(coin, fees) :
    try:

        df = pyupbit.get_ohlcv(coin, interval = "day", count = 7)
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
                    if rtnlist_for['market'] == exceptItemFor:
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

# -----------------------------------------------------------------------------
# - Name : get_candle
# - Desc : 캔들 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 조회 범위
# - Output
#   1) 캔들 정보 배열
# -----------------------------------------------------------------------------
def get_candle(target_item, tick_kind, inq_range):
    try:

        # ----------------------------------------
        # Tick 별 호출 URL 설정
        # ----------------------------------------
        # 분붕
        if tick_kind == "1" or tick_kind == "3" or tick_kind == "5" or tick_kind == "10" or tick_kind == "15" or tick_kind == "30" or tick_kind == "60" or tick_kind == "240":
            target_url = "minutes/" + tick_kind
        # 일봉
        elif tick_kind == "D":
            target_url = "days"
        # 주봉
        elif tick_kind == "W":
            target_url = "weeks"
        # 월봉
        elif tick_kind == "M":
            target_url = "months"
        # 잘못된 입력
        else:
            raise Exception("잘못된 틱 종류:" + str(tick_kind))

        logging.debug(target_url)

        # ----------------------------------------
        # Tick 조회
        # ----------------------------------------
        querystring = {"market": target_item, "count": inq_range}
        res = send_request("GET", server_url + "/v1/candles/" + target_url, querystring, "")
        candle_data = res.json()

        logging.debug(candle_data)

        return candle_data

    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise

# -----------------------------------------------------------------------------
# - Name : get_order_status
# - Desc : 주문 조회(상태별)
# - Input
#   1) target_item : 대상종목
#   2) status : 주문상태(wait : 체결 대기, watch : 예약주문 대기, done : 전체 체결 완료, cancel : 주문 취소)
# - Output
#   1) 주문 내역
# -----------------------------------------------------------------------------
def get_order_status(target_item, status):
    try:

        query = {
            'market': target_item,
            'state': status,
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
    
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

# -----------------------------------------------------------------------------
# - Name : orderby_dict
# - Desc : 딕셔너리 정렬
# - Input
#   1) target_dict : 정렬 대상 딕셔너리
#   2) target_column : 정렬 대상 딕셔너리
#   3) order_by : 정렬방식(False:오름차순, True,내림차순)
# - Output
#   1) 정렬된 딕서너리
# -----------------------------------------------------------------------------
def orderby_dict(target_dict, target_column, order_by):
    try:

        rtn_dict = sorted(target_dict, key=(lambda x: x[target_column]), reverse=order_by)

        return rtn_dict

    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

# -----------------------------------------------------------------------------
# - Name : filter_dict
# - Desc : 딕셔너리 필터링
# - Input
#   1) target_dict : 정렬 대상 딕셔너리
#   2) target_column : 정렬 대상 컬럼
#   3) filter : 필터
# - Output
#   1) 필터링된 딕서너리
# -----------------------------------------------------------------------------
def filter_dict(target_dict, target_column, filter):
    try:

        for target_dict_for in target_dict[:]:
            if target_dict_for[target_column] != filter:
                target_dict.remove(target_dict_for)

        return target_dict

    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise


def get_indicators(target_item, tick_kind, inq_range, loop_cnt):
    try:
        indicator_data = []
        candle_datas = []
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        if len(candle_data) >= 30:
            for i in range(0, int(loop_cnt)):
                candle_datas.append(candle_data[i:int(len(candle_data))])
            rsi_data = get_rsi(candle_datas)
            mfi_data = get_mfi(candle_datas)
            macd_data = get_macd(candle_datas, loop_cnt)
            bb_data = get_bb(candle_datas)
            williams_data = get_williams(candle_datas)
 
            if len(rsi_data) > 0:
                indicator_data.append(rsi_data)
 
            if len(mfi_data) > 0:
                indicator_data.append(mfi_data)
 
            if len(macd_data) > 0:
                indicator_data.append(macd_data)
 
            if len(bb_data) > 0:
                indicator_data.append(bb_data)
 
            if len(williams_data) > 0:
                indicator_data.append(williams_data)
 
        return indicator_data

    except Exception:
        raise


def get_candle(target_item, tick_kind, inq_range):
    try:
 
        if tick_kind == "1" or tick_kind == "3" or tick_kind == "5" or tick_kind == "10" or tick_kind == "15" or tick_kind == "30" or tick_kind == "60" or tick_kind == "240":
            target_url = "minutes/" + tick_kind
        elif tick_kind == "D":
            target_url = "days"
        elif tick_kind == "W":
            target_url = "weeks"
        elif tick_kind == "M":
            target_url = "months"
        else:
            raise Exception("잘못된 틱 종류:" + str(tick_kind))
 
        logging.debug(target_url)
 
        querystring = {"market": target_item, "count": inq_range}
        res = send_request("GET", server_url + "/v1/candles/" + target_url, querystring, "")
        candle_data = res.json()
 
        logging.debug(candle_data)
 
        return candle_data

    except Exception:
        raise


def get_rsi(candle_datas):
    try:
 
        rsi_data = []
 
        for candle_data_for in candle_datas:
 
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.reindex(index=df.index[::-1]).reset_index()
 
            df['close'] = df["trade_price"]
 
            def rsi(ohlc: pd.DataFrame, period: int = 14):
                ohlc["close"] = ohlc["close"]
                delta = ohlc["close"].diff()
 
                up, down = delta.copy(), delta.copy()
                up[up < 0] = 0
                down[down > 0] = 0
 
                _gain = up.ewm(com=(period - 1), min_periods=period).mean()
                _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
 
                RS = _gain / _loss
                return pd.Series(100 - (100 / (1 + RS)), name="RSI")
 
            rsi = round(rsi(df, 14).iloc[-1], 4)
            rsi_data.append({"type": "RSI", "DT": dfDt[0], "RSI": rsi})
 
        return rsi_data
 
    except Exception:
        raise

def get_mfi(candle_datas):
    try:
 
        mfi_list = []
        for candle_data_for in candle_datas:
 
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
 
            df['typical_price'] = (df['trade_price'] + df['high_price'] + df['low_price']) / 3
            df['money_flow'] = df['typical_price'] * df['candle_acc_trade_volume']
 
            positive_mf = 0
            negative_mf = 0
 
            for i in range(0, 14):
 
                if df["typical_price"][i] > df["typical_price"][i + 1]:
                    positive_mf = positive_mf + df["money_flow"][i]
                elif df["typical_price"][i] < df["typical_price"][i + 1]:
                    negative_mf = negative_mf + df["money_flow"][i]
 
            if negative_mf > 0:
                mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
            else:
                mfi = 100 - (100 / (1 + (positive_mf)))
 
            mfi_list.append({"type": "MFI", "DT": dfDt[0], "MFI": round(mfi, 4)})
 
        return mfi_list
 
    except Exception:
        raise

def get_macd(candle_datas, loop_cnt):
    try:
 
        macd_list = []
 
        df = pd.DataFrame(candle_datas[0])
        df = df.iloc[::-1]
        df = df['trade_price']
 
        exp1 = df.ewm(span=12, adjust=False).mean()
        exp2 = df.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()
 
        for i in range(0, int(loop_cnt)):
            macd_list.append(
                {"type": "MACD", "DT": candle_datas[0][i]['candle_date_time_kst'], "MACD": round(macd[i], 4),
                 "SIGNAL": round(exp3[i], 4),
                 "OCL": round(macd[i] - exp3[i], 4)})
 
        return macd_list

    except Exception:
        raise

def get_bb(candle_datas):
    try:
 
        bb_list = []

        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df['trade_price'].iloc[::-1]

            unit = 2
 
            band1 = unit * np.std(df[len(df) - 20:len(df)])
            bb_center = np.mean(df[len(df) - 20:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1
 
            bb_list.append({"type": "BB", "DT": dfDt[0], "BBH": round(band_high, 4), "BBM": round(bb_center, 4),
                            "BBL": round(band_low, 4)})
 
        return bb_list
 
    except Exception:
        raise

def get_williams(candle_datas):
    try:
 
        williams_list = []
 
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.iloc[:14]
 
            hh = np.max(df['high_price'])
            ll = np.min(df['low_price'])
            cp = df['trade_price'][0]
 
            w = (hh - cp) / (hh - ll) * -100
 
            williams_list.append(
                {"type": "WILLIAMS", "DT": dfDt[0], "HH": round(hh, 4), "LL": round(ll, 4), "CP": round(cp, 4),
                 "W": round(w, 4)})
 
        return williams_list
 
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
