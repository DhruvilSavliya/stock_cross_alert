import streamlit as st
import pandas as pd
from cross_alert import analyze_stocks, search_ticker
import json
import os

st.set_page_config(page_title="Stock Watchlist", page_icon="📈", layout="wide")
st.title("📊 Stock Watchlist — Golden/Death Cross Tracker")

# ------------------------------
# JSON-based Watchlist (local)
# ------------------------------
WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    return []

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f)

watchlist = load_watchlist()

# ------------------------------
# Search box for ticker
# ------------------------------
st.subheader("🔍 Add Tickers to Your Watchlist")
query = st.text_input("Search by company name or ticker (e.g. Apple, Tesla, NVDA):")
if query:
    suggestions = search_ticker(query)
    if suggestions:
        selected = st.selectbox("Select from suggestions:", suggestions)
        if st.button("Add Selected"):
            ticker = selected.split(" — ")[0]
            if ticker not in watchlist:
                watchlist.append(ticker)
                save_watchlist(watchlist)
                st.experimental_rerun()
            else:
                st.info(f"{ticker} is already in your watchlist.")

# ------------------------------
# Manage Watchlist
# ------------------------------
st.subheader("🗑️ Manage Watchlist")
if watchlist:
    st.write("**Current Watchlist:**")
    st.write(", ".join(watchlist))

    remove_ticker = st.selectbox("Select a ticker to remove:", [""] + watchlist)
    if st.button("Remove"):
        if remove_ticker:
            watchlist.remove(remove_ticker)
            save_watchlist(watchlist)
            st.experimental_rerun()
else:
    st.info("Your watchlist is empty. Add some tickers above 👆")

# ------------------------------
# Analyze tickers
# ------------------------------
if watchlist:
    st.markdown("---")
    st.subheader("📈 Watchlist Analysis")

    col1, col2, col3, col4 = st.columns([0.3, 1, 1, 0.3])
    with col1:
        analyze_clicked = st.button("📊 Analyze Watchlist")
    with col4:
        refresh_clicked = st.button("🔄 Refresh Data")

    if refresh_clicked:
        try:
            st.cache_data.clear()
        except AttributeError:
            st.caching.clear_cache()
        st.success("✅ Cache cleared — next analysis will fetch fresh data.")

    if analyze_clicked:
        with st.spinner("Analyzing tickers... please wait ⏳"):
            results = analyze_stocks(watchlist, period="2y", interval="1d")

        rows = []
        for ticker, info in results.items():
            df_data = info.get("data")
            last_row = df_data.iloc[-1] if df_data is not None and not df_data.empty else None

            close = last_row["Close"] if last_row is not None and "Close" in last_row.index else None
            sma50 = last_row["SMA50"] if last_row is not None and "SMA50" in last_row.index else None
            sma200 = last_row["SMA200"] if last_row is not None and "SMA200" in last_row.index else None
            rsi = last_row["RSI14"] if last_row is not None and "RSI14" in last_row.index else None
            momentum = last_row["Close"] - last_row["SMA50"] if last_row is not None and "SMA50" in last_row.index else None

            # Suggestion based on RSI
            if rsi is not None:
                if rsi >= 70:
                    suggest = "Take Profit"
                elif rsi <= 30:
                    suggest = "Buy Opportunity"
                else:
                    suggest = "Hold/No Action"
            else:
                suggest = "N/A"

            rows.append({
                "Ticker": ticker,
                "Close": close,
                "50-MA": sma50,
                "200-MA": sma200,
                "RSI14": rsi,
                "Momentum": momentum,
                "Status": info["status"],
                "Current Cross": info["current_cross"],
                "Suggestion": suggest,
                "AI Signal": info.get("ai_signal")
            })

        df = pd.DataFrame(rows)

        def color_status(val):
            if "Golden" in str(val):
                return "color: green; font-weight: bold;"
            elif "Death" in str(val):
                return "color: red; font-weight: bold;"
            else:
                return "color: white;"

        def color_rsi(val):
            if val is None:
                return ""
            elif val >= 70:
                return "background-color: green; color: white; font-weight: bold;"
            elif val <= 30:
                return "background-color: red; color: white; font-weight: bold;"
            else:
                return ""

        styled_df = (
            df.style
            .map(color_status, subset=["Status", "Current Cross"])
            .map(color_rsi, subset=["RSI14"])
            .format({
                "Close": "{:.2f}",
                "50-MA": "{:.2f}",
                "200-MA": "{:.2f}",
                "RSI14": "{:.2f}",
                "Momentum": "{:.2f}"
            })
        )

        st.dataframe(styled_df, use_container_width=True)
