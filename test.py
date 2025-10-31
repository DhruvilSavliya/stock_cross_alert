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

# import yfinance as yf
# import pandas as pd
#
# pd.set_option('display.max_rows', 50)
# pd.set_option('display.max_columns', 15)
# pd.set_option('display.width', 1000)
# pd.set_option('display.max_colwidth', None)
#
# #--- CONFIGRATION ---
# # stocks = ["AAPL", "MSFT", "GOOGL", "NOK"]
# stocks = ["AAPL"]
# short_window = 50
# long_window = 200
#
# # Flag to track if any cross is found
# found_signal = False
#
# for symbol in stocks:
#     data = yf.download(symbol, period="2y", interval="1d", auto_adjust=False)
#     data["SMA50"] = data["Close"].rolling(short_window).mean().round(2)
#     data["SMA200"] = data["Close"].rolling(long_window).mean().round(2)
#
#     # Detect crossover
#     if (
#         data["SMA50"].iloc[-2] < data["SMA200"].iloc[-2] and
#         data["SMA50"].iloc[-1] > data["SMA200"].iloc[-1]
#     ):
#         print(f"🔔 Golden Cross on {symbol}")
#         found_signal = True
#     elif (
#         data["SMA50"].iloc[-2] > data["SMA200"].iloc[-2] and
#         data["SMA50"].iloc[-1] < data["SMA200"].iloc[-1]
#     ):
#         print(f"⚠️ Death Cross on {symbol}")
#         found_signal = True
#
#
#
# # If no crosses were found
# if not found_signal:
#     print("No Golden Cross or Death Cross found for any stock today.")
#
#
# #print(data.tail(3))