import pyupbit
import numpy as np

#OHLCV(open, hig, low, close, volume ) 7일간
df = pyupbit.get_ohlcv("KRW-ADA", count = 7)


#변동폭 * K 계산, (고가 - 저가) * k값
df['range'] = (df['high'] - df['low']) * 0.5

#target(매수가), range 컬럼을 한칸씩 밑으로 내림(.shift(1))
df['target'] = df['open'] + df['range'].shift(1)

# ror(수익율) , np.where(조건문, 참일때 값, 거짓일때 값)
df['ror'] = np.where(df['high'] > df['target'], 
                     df['close'] / df['target'], 
                     1)     
#누적 곱 계산(cumprod) ==> 누적 수익률
df['hpr'] = df['ror'].cumprod()

# Drow Down 계산(누적 최대 값과 현재 hpr 차이 / 누적 최대값 * 100)
df['dd'] = (df['hpr'].cummax() - df['hpr']) / df['hpr'].cummax() * 100

# MDD 계싼
print("MOD(%): ", df['dd'].max())

# 엑셀저장
df.to_excel("dd.xlsx")