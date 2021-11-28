import time
import logging
import traceback
from numpy.core.numeric import False_
import requests
import jwt
from urllib.parse import urlencode
from decimal import Decimal
import uuid
import sys
import math
import pandas as pd
import numpy
import hashlib

# Keys
access_key = ""
secret_key = ""
server_url = 'https://api.upbit.com'


min_order_amt = 5000

sell_pcnt = 5

dcnt_pcnt = -3

# sell_except_item = ["LOOM"]  
sell_except_item = []  


def start_seconddream():

    try:

        set_loglevel("E")    
 
        # ----------------------------------------------------------------------
        # 반복 수행
        # ----------------------------------------------------------------------
        while True:
 
            # ------------------------------------------------------------------
            # 보유 종목조회
            # ------------------------------------------------------------------
            target_items = get_accounts('Y', 'KRW')
 
            # ------------------------------------------------------------------
            # 보유 종목 현재가 조회
            # ------------------------------------------------------------------
            target_items_comma = chg_account_to_comma(target_items)
            tickers = get_ticker(target_items_comma)
 
            # -----------------------------------------------------------------
            # 보유 종목별 진행
            # -----------------------------------------------------------------
            for target_item in target_items:
                for ticker in tickers:
                    if target_item['market'] == ticker['market']:
 
                        # -----------------------------------------------------
                        # 수익률 계산
                        # ((현재가 - 평균매수가) / 평균매수가) * 100
                        # -----------------------------------------------------
                        rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(target_item['avg_buy_price']))) / Decimal(str(target_item['avg_buy_price']))) * 100, 2)
 
                        logging.info('')
                        logging.info('------------------------------------------------------')
                        logging.info('- 종목:' + str(target_item['market']))
                        logging.info('- 평균매수가:' + str(target_item['avg_buy_price']))
                        logging.info('- 현재가:' + str(ticker['trade_price']))
                        logging.info('- 수익률:' + str(rev_pcnt))
 
                        # -----------------------------------------------------
                        # 현재 수익률이 매도 수익률 이상인 경우에만 진행
                        # -----------------------------------------------------
                        if Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)):
                            logging.info('- 현재 수익률이 매도 수익률 보다 낮아 진행하지 않음!!!')
                            logging.info('------------------------------------------------------')
                            continue


                        # -----------------------------------------------------
                        # 고점대비 하락률
                        # ((현재가 - 최고가) / 최고가) * 100
                        # -----------------------------------------------------
                        cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(ticker['high_price']))) / Decimal(str(ticker['high_price']))) * 100, 2)

                        logging.info('- 금일 최고가:' + str(ticker['high_price']))
                        logging.info('- 고점대비 하락률:' + str(cur_dcnt_pcnt))
                        
                        if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(dcnt_pcnt)):
                                
                            # ------------------------------------------------------------------
                            # 시장가 매도
                            # 실제 매도 로직은 안전을 위해 주석처리 하였습니다.
                            # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                            # ------------------------------------------------------------------
                            logging.info('시장가 매도 시작! [' + str(target_item['market']) + ']')
                            rtn_sellcoin_mp = sellcoin_mp(target_item['market'], 'Y')
                            logging.info('시장가 매도 종료! [' + str(target_item['market']) + ']')
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
 
        williams_list = []
 
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.iloc[:14]
 
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
        logging.info("buy end!")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
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
