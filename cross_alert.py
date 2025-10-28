import yfinance as yf
import pandas as pd

symbol = "AAPL"

# Download 1 year of daily data
data = yf.download(symbol, period="1y", interval="1d")

print(data.tail())
