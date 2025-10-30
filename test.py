import yfinance as yf
import pandas as pd

pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 15)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

#--- CONFIGRATION ---
symbol = ["NOK"]
short_window = 50
long_window = 200

# Download data for multiple tickers
data = yf.download(symbol, period="2y", interval="1d", auto_adjust=False)

data["SMA50"] = data["Close"].rolling(short_window).mean()
data["SMA200"] = data["Close"].rolling(long_window).mean()

print(data.tail())