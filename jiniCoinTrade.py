import time
import logging
import traceback
from numpy.core.numeric import False_
import requests
import jwt
from urllib.parse import urlencode
from decimal import Decimal
import uuid
import os
import sys
import math
import pandas as pd
import numpy
import hashlib

# Keys
access_key = "업비트 번호"
secret_key = "업비트 번호"
server_url = 'https://api.upbit.com'

min_order_amt = 5000

buy_amt = 10000  

buy_except_items = ""

sell_except_item = ["ADA", "OMG", "GLM"]  


def start_seconddream():
    try:

        set_loglevel("I")    

        while True:
            # 1. available amt
            available_amt = get_krwbal()['available_krw']
            # 2. my coin list
            my_items = get_accounts('Y','KRW')
            my_items_comma = chg_account_to_comma(my_items)
            tickers = get_ticker(my_items_comma)

            if available_amt > buy_amt :  

                target_items = get_items('KRW', buy_except_items)
                
                for target_item in target_items:
                    rsi_val = False
                    mfi_val = False
                    ocl_val = False
                    logging.info('Checking....[' + str(target_item['market']) + ']')

                    indicators_data = get_indicators(target_item['market'], 'D', 200, 5)

                    if len(indicators_data) < 5:
                        logging.info('except item....[' + str(target_item['market']) + ']')
                        continue                

                    if (Decimal(str(indicators_data[0][0]['RSI'])) > Decimal(str(indicators_data[0][1]['RSI']))
                        and Decimal(str(indicators_data[0][1]['RSI'])) > Decimal(str(40))):
                        rsi_val = True 

                    if (Decimal(str(indicators_data[1][0]['MFI'])) > Decimal(str(indicators_data[1][1]['MFI']))
                        and Decimal(str(indicators_data[1][1]['MFI'])) > Decimal(str(indicators_data[1][2]['MFI']))
                        and Decimal(str(indicators_data[1][0]['MFI'])) > Decimal(str(40))):

                        mfi_val = True

                    if (Decimal(str(indicators_data[2][0]['OCL'])) > Decimal(str(indicators_data[2][1]['OCL']))
                        and Decimal(str(indicators_data[2][1]['OCL'])) > Decimal(str(indicators_data[2][2]['OCL']))
                        and Decimal(str(indicators_data[2][3]['OCL'])) > Decimal(str(indicators_data[2][2]['OCL']))
                        and Decimal(str(indicators_data[2][1]['OCL'])) < Decimal(str(0))
                        and Decimal(str(indicators_data[2][2]['OCL'])) < Decimal(str(0))
                        and Decimal(str(indicators_data[2][3]['OCL'])) < Decimal(str(0))):
                        ocl_val = True

                    if rsi_val and mfi_val and ocl_val:

                        logging.info('find item....[' + str(target_item['market']) + ']')
                        logging.info(indicators_data[0])
                        logging.info(indicators_data[1])
                        logging.info(indicators_data[2])                    

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

                # -----------------------------------------------------------------
                # 보유 종목별 진행
                # -----------------------------------------------------------------
                for my_item in my_items:
                    for ticker in tickers:
                        if my_item['market'].split('-')[1] not in sell_except_item :                         
                            if my_item['market'] == ticker['market']:
        
                                # -----------------------------------------------------
                                # 수익률 계산
                                # ((현재가 - 평균매수가) / 평균매수가) * 100
                                # -----------------------------------------------------
                                rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(my_item['avg_buy_price']))) / Decimal(str(my_item['avg_buy_price']))) * 100, 2)
        
                                logging.info('')
                                logging.info('------------------------------------------------------')
                                logging.info('- 종목:' + str(my_item['market']))
                                logging.info('- 평균매수가:' + str(my_item['avg_buy_price']))
                                logging.info('- 현재가:' + str(ticker['trade_price']))
                                logging.info('- 수익률:' + str(rev_pcnt))
        
                                # -----------------------------------------------------
                                # 현재 수익률이 매도 수익률 이상인 경우에만 진행
                                # -----------------------------------------------------
                                if Decimal(str(rev_pcnt)) < Decimal(str(2)):
                                    logging.info('- 현재 수익률이 매도 수익률 보다 낮아 진행하지 않음!!!')
                                    logging.info('------------------------------------------------------')
                                    continue
        
                                # -------------------------------------------------
                                # 고점을 계산하기 위해 최근 매수일자 조회
                                # 1. 해당 종목에 대한 거래 조회(done, cancel)
                                # 2. 거래일시를 최근순으로 정렬
                                # 3. 매수 거래만 필터링
                                # 4. 가장 최근 거래일자부터 현재까지 고점을 조회
                                # -------------------------------------------------
                                order_done = get_order_status(my_item['market'], 'done') + get_order_status(my_item['market'], 'cancel')
                                order_done_sorted = orderby_dict(order_done, 'created_at', True)
                                order_done_filtered = filter_dict(order_done_sorted, 'side', 'bid')
        
                                # ------------------------------------------------------------------
                                # 캔들 조회
                                # ------------------------------------------------------------------
                                candles = get_candle(my_item['market'], 'D', 200)
        
                                # ------------------------------------------------------------------
                                # 최근 매수일자 다음날부터 현재까지의 최고가를 계산
                                # ------------------------------------------------------------------
                                df = pd.DataFrame(candles)
                                mask = df['candle_date_time_kst'] > order_done_filtered[0]['created_at']
                                filtered_df = df.loc[mask]
        
                                higest_high_price = numpy.max(filtered_df['high_price'])
        
                                # -----------------------------------------------------
                                # 고점대비 하락률
                                # ((현재가 - 최고가) / 최고가) * 100
                                # -----------------------------------------------------
                                cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(higest_high_price))) / Decimal(str(higest_high_price))) * 100, 2)
        
                                logging.info('- 매수 후 최고가:' + str(higest_high_price))
                                logging.info('- 고점대비 하락률:' + str(cur_dcnt_pcnt))
                                
                                if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(-1)):
                                        
                                    # ------------------------------------------------------------------
                                    # 시장가 매도
                                    # 실제 매도 로직은 안전을 위해 주석처리 하였습니다.
                                    # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                                    # ------------------------------------------------------------------
                                    logging.info('시장가 매도 시작! [' + str(my_item['market']) + ']')
                                    rtn_sellcoin_mp = sellcoin_mp(my_item['market'], 'Y')
                                    logging.info('시장가 매도 종료! [' + str(my_item['market']) + ']')
                                    logging.info(rtn_sellcoin_mp)
                                    logging.info('------------------------------------------------------')
        
                                else:
                                    logging.info('- 고점 대비 하락률 조건에 맞지 않아 매도하지 않음!!!')
                                    logging.info('------------------------------------------------------')  





            else :
                # -----------------------------------------------------------------
                # 보유 종목별 진행
                # -----------------------------------------------------------------
                for my_item in my_items:
                    for ticker in tickers:
                        if my_item['market'].split('-')[1] not in sell_except_item :                         
                            if my_item['market'] == ticker['market']:
        
                                # -----------------------------------------------------
                                # 수익률 계산
                                # ((현재가 - 평균매수가) / 평균매수가) * 100
                                # -----------------------------------------------------
                                rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(my_item['avg_buy_price']))) / Decimal(str(my_item['avg_buy_price']))) * 100, 2)
        
                                logging.info('')
                                logging.info('------------------------------------------------------')
                                logging.info('- 종목:' + str(my_item['market']))
                                logging.info('- 평균매수가:' + str(my_item['avg_buy_price']))
                                logging.info('- 현재가:' + str(ticker['trade_price']))
                                logging.info('- 수익률:' + str(rev_pcnt))
        
                                # -----------------------------------------------------
                                # 현재 수익률이 매도 수익률 이상인 경우에만 진행
                                # -----------------------------------------------------
                                if Decimal(str(rev_pcnt)) < Decimal(str(2)):
                                    logging.info('- 현재 수익률이 매도 수익률 보다 낮아 진행하지 않음!!!')
                                    logging.info('------------------------------------------------------')
                                    continue
        
                                # -------------------------------------------------
                                # 고점을 계산하기 위해 최근 매수일자 조회
                                # 1. 해당 종목에 대한 거래 조회(done, cancel)
                                # 2. 거래일시를 최근순으로 정렬
                                # 3. 매수 거래만 필터링
                                # 4. 가장 최근 거래일자부터 현재까지 고점을 조회
                                # -------------------------------------------------
                                order_done = get_order_status(my_item['market'], 'done') + get_order_status(my_item['market'], 'cancel')
                                order_done_sorted = orderby_dict(order_done, 'created_at', True)
                                order_done_filtered = filter_dict(order_done_sorted, 'side', 'bid')
        
                                # ------------------------------------------------------------------
                                # 캔들 조회
                                # ------------------------------------------------------------------
                                candles = get_candle(my_item['market'], 'D', 200)
        
                                # ------------------------------------------------------------------
                                # 최근 매수일자 다음날부터 현재까지의 최고가를 계산
                                # ------------------------------------------------------------------
                                df = pd.DataFrame(candles)
                                mask = df['candle_date_time_kst'] > order_done_filtered[0]['created_at']
                                filtered_df = df.loc[mask]
        
                                higest_high_price = numpy.max(filtered_df['high_price'])
        
                                # -----------------------------------------------------
                                # 고점대비 하락률
                                # ((현재가 - 최고가) / 최고가) * 100
                                # -----------------------------------------------------
                                cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(higest_high_price))) / Decimal(str(higest_high_price))) * 100, 2)
        
                                logging.info('- 매수 후 최고가:' + str(higest_high_price))
                                logging.info('- 고점대비 하락률:' + str(cur_dcnt_pcnt))
                                
                                if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(-1)):
                                        
                                    # ------------------------------------------------------------------
                                    # 시장가 매도
                                    # 실제 매도 로직은 안전을 위해 주석처리 하였습니다.
                                    # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                                    # ------------------------------------------------------------------
                                    logging.info('시장가 매도 시작! [' + str(my_item['market']) + ']')
                                    rtn_sellcoin_mp = sellcoin_mp(my_item['market'], 'Y')
                                    logging.info('시장가 매도 종료! [' + str(my_item['market']) + ']')
                                    logging.info(rtn_sellcoin_mp)
                                    logging.info('------------------------------------------------------')
        
                                else:
                                    logging.info('- 고점 대비 하락률 조건에 맞지 않아 매도하지 않음!!!')
                                    logging.info('------------------------------------------------------')  


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
 
        # 잔고가 있는 경우만
        if Decimal(str(krw_balance)) > Decimal(str(0)):
            # 수수료
            fee = math.ceil(Decimal(str(krw_balance)) * (Decimal(str(fee_rate)) / Decimal(str(100))))
 
            # 매수가능금액
            available_krw = math.floor(Decimal(str(krw_balance)) - Decimal(str(fee)))
 
        else:
            # 수수료
            fee = 0
 
            # 매수가능금액
            available_krw = 0
 
        # 결과 조립
        rtn_balance['krw_balance'] = krw_balance
        rtn_balance['fee'] = fee
        rtn_balance['available_krw'] = available_krw
 
        return rtn_balance
 
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
 
            # KRW 및 소액 제외
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


def get_items(market, except_item):
    try:
 
        # 조회결과 리턴용
        rtn_list = []
 
        # 마켓 데이터
        markets = market.split(',')
 
        # 제외 데이터
        except_items = except_item.split(',')
 
        url = "https://api.upbit.com/v1/market/all"
        querystring = {"isDetails": "false"}
        response = send_request("GET", url, querystring, "")
        data = response.json()
 
        # 조회 마켓만 추출
        for data_for in data:
            for market_for in markets:
                if data_for['market'].split('-')[0] == market_for:
                    rtn_list.append(data_for)
 
        # 제외 종목 제거
        for rtnlist_for in rtn_list[:]:
            for exceptItemFor in except_items:
                for marketFor in markets:
                    if rtnlist_for['market'] == marketFor + '-' + exceptItemFor:
                        rtn_list.remove(rtnlist_for)
 
        return rtn_list

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

def get_indicators(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 보조지표 리턴용
        indicator_data = []
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        if len(candle_data) >= 30:
 
            # 조회 횟수별 candle 데이터 조합
            for i in range(0, int(loop_cnt)):
                candle_datas.append(candle_data[i:int(len(candle_data))])
 
            # RSI 정보 조회
            rsi_data = get_rsi(candle_datas)
 
            # MFI 정보 조회
            mfi_data = get_mfi(candle_datas)
 
            # MACD 정보 조회
            macd_data = get_macd(candle_datas, loop_cnt)
 
            # BB 정보 조회
            bb_data = get_bb(candle_datas)
 
            # WILLIAMS %R 조회
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


def get_rsi(candle_datas):
    try:
 
        # RSI 데이터 리턴용
        rsi_data = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
 
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.reindex(index=df.index[::-1]).reset_index()
 
            df['close'] = df["trade_price"]
 
            # RSI 계산
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
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

def get_mfi(candle_datas):
    try:
 
        # MFI 데이터 리턴용
        mfi_list = []
 
        # 캔들 데이터만큼 수행
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
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

def get_macd(candle_datas, loop_cnt):
    try:
 
        # MACD 데이터 리턴용
        macd_list = []
 
        df = pd.DataFrame(candle_datas[0])
        df = df.iloc[::-1]
        df = df['trade_price']
 
        # MACD 계산
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
 
        # 볼린저밴드 데이터 리턴용
        bb_list = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df['trade_price'].iloc[::-1]
 
            # 표준편차(곱)
            unit = 2
 
            band1 = unit * numpy.std(df[len(df) - 20:len(df)])
            bb_center = numpy.mean(df[len(df) - 20:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1
 
            bb_list.append({"type": "BB", "DT": dfDt[0], "BBH": round(band_high, 4), "BBM": round(bb_center, 4),
                            "BBL": round(band_low, 4)})
 
        return bb_list
 
    except Exception:
        raise

def get_williams(candle_datas):
    try:
 
        # 윌리암스R 데이터 리턴용
        williams_list = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.iloc[:14]
 
            # 계산식
            # %R = (Highest High - Close)/(Highest High - Lowest Low) * -100
            hh = numpy.max(df['high_price'])
            ll = numpy.min(df['low_price'])
            cp = df['trade_price'][0]
 
            w = (hh - cp) / (hh - ll) * -100
 
            williams_list.append(
                {"type": "WILLIAMS", "DT": dfDt[0], "HH": round(hh, 4), "LL": round(ll, 4), "CP": round(cp, 4),
                 "W": round(w, 4)})
 
        return williams_list
 
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
        logging.info("시장가 매수 완료!")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise

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

def sellcoin_mp(target_item, cancel_yn):
    try:
 
        if cancel_yn == 'Y':
            # 기존 주문이 있으면 취소
            cancel_order(target_item, "SELL")
 
        # 잔고 조회
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
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise

def cancel_order(target_item, side):
    try:
 
        # 미체결 주문 조회
        order_data = get_order(target_item)
 
        # 매수/매도 구분
        for order_data_for in order_data:
 
            if side == "BUY" or side == "buy":
                if order_data_for['side'] == "ask":
                    order_data.remove(order_data_for)
            elif side == "SELL" or side == "sell":
                if order_data_for['side'] == "bid":
                    order_data.remove(order_data_for)
 
        # 미체결 주문이 있으면
        if len(order_data) > 0:
 
            # 미체결 주문내역 전체 취소
            for order_data_for in order_data:
                cancel_order_uuid(order_data_for['uuid'])
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
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

def orderby_dict(target_dict, target_column, order_by):
    try:
 
        rtn_dict = sorted(target_dict, key=(lambda x: x[target_column]), reverse=order_by)
 
        return rtn_dict
 
    except Exception:
        raise


def filter_dict(target_dict, target_column, filter):
    try:
 
        for target_dict_for in target_dict[:]:
            if target_dict_for[target_column] != filter:
                target_dict.remove(target_dict_for)
 
        return target_dict
 
    except Exception:
        raise


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


if __name__ == '__main__':
 
    # noinspection PyBroadException
    try:

        # start
        start_seconddream()


    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)
 
    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)