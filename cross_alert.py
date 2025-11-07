import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from yahooquery import search

# ------------------------------
# CONFIG
# ------------------------------
BATCH_SIZE = 100
MAX_WORKERS = 5
CACHE_TTL = 3600  # 1 hour
MIN_DAYS = 200
# ------------------------------

pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 15)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

# ------------------------------
# Logging helper
# ------------------------------
def log(message):
    """Append message to session_state log and display in Streamlit."""
    if "log_area" not in st.session_state:
        st.session_state["log_area"] = []
    st.session_state["log_area"].append(str(message))
    st.write(str(message))  # Show in UI

# ------------------------------
# Download batch of tickers
# ------------------------------
def _download_batch(tickers, period="2y", interval="1d"):
    try:
        data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=False,
            threads=True,
            progress=False
        )
        log(f"✅ Downloaded batch: {tickers}")
        return data
    except Exception as e:
        log(f"❌ Error fetching batch {tickers}: {e}")
        return pd.DataFrame()

# ------------------------------
# Analyze single ticker
# ------------------------------
def _analyze_single_ticker(ticker, df):
    if df.empty or "Close" not in df.columns:
        log(f"⚠️ {ticker}: No data available")
        return {"status": "No Data", "data": None}

    df = df.dropna().copy()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    if len(df) < MIN_DAYS:
        log(f"⚠️ {ticker}: Insufficient data (only {len(df)} days)")
        return {"status": "Insufficient Data", "data": df}

    prev_50, prev_200 = df["SMA50"].iloc[-2], df["SMA200"].iloc[-2]
    last_50, last_200 = df["SMA50"].iloc[-1], df["SMA200"].iloc[-1]

    # Log the last few MA values for debugging
    log(f"{ticker}: Last Close={df['Close'].iloc[-1]:.2f}, SMA50={last_50:.2f}, SMA200={last_200:.2f}")

    if np.isnan(prev_50) or np.isnan(prev_200) or np.isnan(last_50) or np.isnan(last_200):
        status = "Insufficient Data"
    elif prev_50 < prev_200 and last_50 > last_200:
        status = "Golden Cross"
    elif prev_50 > prev_200 and last_50 < last_200:
        status = "Death Cross"
    else:
        status = "No Cross"

    return {"status": status, "data": df}

# ------------------------------
# Analyze multiple tickers
# ------------------------------
@st.cache_data(ttl=CACHE_TTL)
def analyze_stocks(tickers, period="2y", interval="1d"):
    results = {}
    if not tickers:
        log("⚠️ No tickers to analyze")
        return results

    num_batches = math.ceil(len(tickers) / BATCH_SIZE)
    batches = [tickers[i * BATCH_SIZE:(i + 1) * BATCH_SIZE] for i in range(num_batches)]

    all_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_download_batch, batch, period, interval): batch for batch in batches}
        for future in as_completed(futures):
            batch = futures[future]
            data = future.result()
            if isinstance(data.columns, pd.MultiIndex):
                for t in batch:
                    if t in data.columns.get_level_values(0):
                        all_data[t] = data[t].dropna()
            else:
                all_data[batch[0]] = data.dropna()

    for ticker in tickers:
        df = all_data.get(ticker, pd.DataFrame())
        results[ticker] = _analyze_single_ticker(ticker, df)

    return results

# ------------------------------
# Search tickers
# ------------------------------
@st.cache_data(ttl=3600)
def search_ticker(query, limit=10):
    if not query or len(query) < 2:
        return []

    try:
        results = search(query)
        quotes = results.get("quotes", [])
        tickers = []
        for q in quotes[:limit]:
            symbol = q.get("symbol")
            name = q.get("shortname") or q.get("longname") or ""
            if symbol and name:
                tickers.append(f"{symbol} — {name}")
        log(f"🔍 Search '{query}' found: {tickers}")
        return tickers
    except Exception as e:
        log(f"❌ Search error for '{query}': {e}")
        return []
