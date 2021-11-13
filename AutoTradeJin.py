import time
import os
import sys
import logging
import traceback
import pandas as pd
import numpy
 
from decimal import Decimal
 
# 공통 모듈 Import
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module import upbit
 
 
# -----------------------------------------------------------------------------
# - Name : start_autotrade
# -----------------------------------------------------------------------------
def start_autotrade():
    try:

        log_level = "I"     
        except_items = "ADA" 
        buy_amt = 50000      
        sell_pcnt = 2
        dcnt_pcnt =-1  

        upbit.set_loglevel(log_level)

        except_item_list = ["ADA", "OMG"]        
 
        #----------------------------------------------------------------------
        # 반복 수행
        #----------------------------------------------------------------------
        while True:

            #가용 금액
            available_amt = upbit.get_krwbal()['available_krw']

            logging.info("*********************************************************")
            logging.info("1. log_level : " + str(log_level))
            logging.info("2. buy_amt : " + str(buy_amt))
            logging.info("3. except_item : " + str(except_items))
            logging.info("4. available_amt :" + str(available_amt))
            logging.info("*********************************************************")
 
            if available_amt > buy_amt :
                target_items = upbit.get_items('KRW', except_items)

                for target_item in target_items:
    
                    rsi_val = False
                    mfi_val = False
                    ocl_val = False
    
                    logging.info('Checking....[' + str(target_item['market']) + ']')
    
                    indicators_data = upbit.get_indicators(target_item['market'], 'D', 200, 5)
    
                    if len(indicators_data) < 5:
                        logging.info('have no data....[' + str(target_item['market']) + ']')
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



                    #--------------------------------------------------------------
                    # find item
                    #--------------------------------------------------------------
                    if rsi_val and mfi_val and ocl_val:
                        logging.info('find buy item....[' + str(target_item['market']) + ']')
                        logging.info(indicators_data[0])
                        logging.info(indicators_data[1])
                        logging.info(indicators_data[2])
     
                        if Decimal(str(available_amt)) < Decimal(str(buy_amt)):
                            logging.info('buy_amt[' + str(available_amt) + ']  < available_amt[' + str(buy_amt) + '] ')
                            continue
    
                        if Decimal(str(buy_amt)) < Decimal(str(upbit.min_order_amt)):
                            logging.info('buy_amt[' + str(buy_amt) + '] < min_order_amt[' + str(upbit.min_order_amt) + '] ')
                            continue
    
                        logging.info('market buy start! [' + str(target_item['market']) + ']')
                        rtn_buycoin_mp = upbit.buycoin_mp(target_item['market'], buy_amt)
                        logging.info('market buy end! [' + str(target_item['market']) + ']')
                        logging.info(rtn_buycoin_mp)
    
                        if except_items.strip():
                            except_items = except_items + ',' + target_item['market'].split('-')[1]
                        else:
                            except_items = target_item['market'].split('-')[1]


                target_items = upbit.get_accounts('Y', 'KRW')

                target_items_comma = upbit.chg_account_to_comma(target_items)
                tickers = upbit.get_ticker(target_items_comma)

                for target_item in target_items:
                    for ticker in tickers:
                        if target_item['market'].split('-')[1] not in except_item_list :                        
                            if target_item['market'] == ticker['market']:
                                rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(target_item['avg_buy_price']))) / Decimal(str(target_item['avg_buy_price']))) * 100, 2)
                                logging.info('')
                                logging.info('------------------------------------------------------')
                                logging.info('- market:' + str(target_item['market']))
                                logging.info('- avg_buy_price:' + str(target_item['avg_buy_price']))
                                logging.info('- trade_price:' + str(ticker['trade_price']))
                                logging.info('- rev_pcnt:' + str(rev_pcnt))
        
                                if Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)):
                                    logging.info('- Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)!!!')
                                    logging.info('------------------------------------------------------')
                                    continue
                                order_done = upbit.get_order_status(target_item['market'], 'done') + upbit.get_order_status(target_item['market'], 'cancel')
                                order_done_sorted = upbit.orderby_dict(order_done, 'created_at', True)
                                order_done_filtered = upbit.filter_dict(order_done_sorted, 'side', 'bid')
        
                                candles = upbit.get_candle(target_item['market'], 'D', 200)
        
                                df = pd.DataFrame(candles)
                                mask = df['candle_date_time_kst'] > order_done_filtered[0]['created_at']
                                filtered_df = df.loc[mask]
        
                                higest_high_price = numpy.max(filtered_df['high_price'])
        
                                cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(higest_high_price))) / Decimal(str(higest_high_price))) * 100, 2)
        
                                logging.info('- higest_high_price:' + str(higest_high_price))
                                logging.info('- cur_dcnt_pcnt:' + str(cur_dcnt_pcnt))
                                
                                if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(dcnt_pcnt)):
                                    logging.info('market sell start! [' + str(target_item['market']) + ']')
                                    rtn_sellcoin_mp = upbit.sellcoin_mp(target_item['market'], 'Y')
                                    logging.info('market sell end! [' + str(target_item['market']) + ']')
                                    logging.info(rtn_sellcoin_mp)
                                    logging.info('------------------------------------------------------')

            else :

                target_items = upbit.get_accounts('Y', 'KRW')

                target_items_comma = upbit.chg_account_to_comma(target_items)
                tickers = upbit.get_ticker(target_items_comma)

                for target_item in target_items:
                    for ticker in tickers:
                        if target_item['market'].split('-')[1] not in except_item_list :                        
                            if target_item['market'] == ticker['market']:
                                rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(target_item['avg_buy_price']))) / Decimal(str(target_item['avg_buy_price']))) * 100, 2)
                                logging.info('')
                                logging.info('------------------------------------------------------')
                                logging.info('- market:' + str(target_item['market']))
                                logging.info('- avg_buy_price:' + str(target_item['avg_buy_price']))
                                logging.info('- trade_price:' + str(ticker['trade_price']))
                                logging.info('- rev_pcnt:' + str(rev_pcnt))

                                if Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)):
                                    logging.info('- Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)!!!')
                                    logging.info('------------------------------------------------------')
                                    continue
                                order_done = upbit.get_order_status(target_item['market'], 'done') + upbit.get_order_status(target_item['market'], 'cancel')
                                order_done_sorted = upbit.orderby_dict(order_done, 'created_at', True)
                                order_done_filtered = upbit.filter_dict(order_done_sorted, 'side', 'bid')

                                candles = upbit.get_candle(target_item['market'], 'D', 200)

                                df = pd.DataFrame(candles)
                                mask = df['candle_date_time_kst'] > order_done_filtered[0]['created_at']
                                filtered_df = df.loc[mask]

                                higest_high_price = numpy.max(filtered_df['high_price'])

                                cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(higest_high_price))) / Decimal(str(higest_high_price))) * 100, 2)

                                logging.info('- higest_high_price:' + str(higest_high_price))
                                logging.info('- cur_dcnt_pcnt:' + str(cur_dcnt_pcnt))
                                
                                if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(dcnt_pcnt)):
                                    logging.info('market sell start! [' + str(target_item['market']) + ']')
                                    rtn_sellcoin_mp = upbit.sellcoin_mp(target_item['market'], 'Y')
                                    logging.info('market sell end! [' + str(target_item['market']) + ']')
                                    logging.info(rtn_sellcoin_mp)
                                    logging.info('------------------------------------------------------')


    # ---------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
# -----------------------------------------------------------------------------
# - Name : main
# - Desc : 메인
# -----------------------------------------------------------------------------
if __name__ == '__main__':
 
    # noinspection PyBroadException
    try:

        start_autotrade()
 
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)
 
    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)