import streamlit as st
import pandas as pd
from cross_alert import analyze_stocks, search_ticker
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Stock Watchlist", page_icon="📈", layout="wide")
st.title("📊 Stock Watchlist — Golden/Death Cross Tracker")

# ------------------------------
# Initialize Firebase (UNCHANGED)
# ------------------------------
firebase_creds = dict(st.secrets["firebase"])

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------------------------
# Firestore Watchlist (UNCHANGED)
# ------------------------------
def get_watchlist():
    docs = db.collection("watchlist").stream()
    return [doc.to_dict()["symbol"] for doc in docs]

watchlist = get_watchlist()

# ------------------------------
# Search box for ticker (UNCHANGED + minor UI improvement)
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
                db.collection("watchlist").add({"symbol": ticker})
                st.success(f"✅ {ticker} added to watchlist!")
                st.rerun()
            else:
                st.info(f"{ticker} is already in your watchlist.")
    else:
        st.warning("No matching tickers found. Try a different name.")

# ------------------------------
# Manage Watchlist (UNCHANGED + st.rerun)
# ------------------------------
st.subheader("🗑️ Manage Watchlist")

if watchlist:
    st.write("**Current Watchlist:**")
    st.write(", ".join(watchlist))

    remove_ticker = st.selectbox("Select a ticker to remove:", [""] + watchlist)

    if st.button("Remove"):
        if remove_ticker:
            docs = db.collection("watchlist").where("symbol", "==", remove_ticker).stream()
            for doc in docs:
                doc.reference.delete()
            st.warning(f"❌ {remove_ticker} removed from watchlist.")
            st.rerun()
else:
    st.info("Your watchlist is empty. Add some tickers above 👆")

# ------------------------------
# Analyze tickers (ENHANCED)
# ------------------------------
if watchlist:
    st.divider()
    st.subheader("📈 Watchlist Analysis")

    col1, col2, col3, col4 = st.columns([0.3, 1, 1, 0.3])
    with col1:
        analyze_clicked = st.button("📊 Analyze Watchlist")
    with col4:
        refresh_clicked = st.button("🔄 Refresh Data")

    if refresh_clicked:
        st.cache_data.clear()
        st.success("✅ Cache cleared — next analysis will fetch fresh data.")

    if analyze_clicked:
        with st.spinner("Analyzing tickers... please wait ⏳"):
            results = analyze_stocks(watchlist, period="2y", interval="1d")

        rows = []
        for ticker, info in results.items():
            df_data = info.get("data")

            if df_data is not None and not df_data.empty:
                last_row = df_data.iloc[-1]
                close = last_row.get("Close")
                sma50 = last_row.get("SMA50")
                sma200 = last_row.get("SMA200")
                rsi = last_row.get("RSI14")
                momentum = close - sma50 if close is not None and sma50 is not None else None
            else:
                close = sma50 = sma200 = rsi = momentum = None

            # Human-based suggestion
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
                "Status": info.get("status"),
                "Current Cross": info.get("current_cross"),
                "Suggestion": suggest,
                "AI Signal": info.get("ai_signal")
            })

        df = pd.DataFrame(rows)

        # ------------------------------
        # Styling Enhancements
        # ------------------------------
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
            if val >= 70:
                return "background-color: green; color: white; font-weight: bold;"
            if val <= 30:
                return "background-color: red; color: white; font-weight: bold;"
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
