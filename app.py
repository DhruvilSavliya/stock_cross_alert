import streamlit as st
import pandas as pd
from cross_alert import analyze_stocks, search_ticker
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Stock Watchlist", page_icon="📈", layout="wide")
st.title("📊 Stock Watchlist — Golden/Death Cross Tracker")

# ------------------------------
# Initialize Firebase
# ------------------------------
firebase_creds = dict(st.secrets["firebase"])  # Make sure secrets.toml has nested [firebase] keys

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------------------------
# Load watchlist from Firestore
# ------------------------------
def get_watchlist():
    docs = db.collection("watchlist").stream()
    return [doc.to_dict()["symbol"] for doc in docs]

watchlist = get_watchlist()

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
                db.collection("watchlist").add({"symbol": ticker})
                st.success(f"✅ {ticker} added to watchlist!")
                watchlist.append(ticker)  # Update local list immediately
            else:
                st.info(f"{ticker} is already in your watchlist.")
    else:
        st.warning("No matching tickers found. Try a different name.")

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
            # Delete from Firestore
            docs = db.collection("watchlist").where("symbol", "==", remove_ticker).stream()
            for doc in docs:
                doc.reference.delete()
            st.warning(f"❌ {remove_ticker} removed from watchlist.")
            watchlist.remove(remove_ticker)
else:
    st.info("Your watchlist is empty. Add some tickers above 👆")

# ------------------------------
# Analyze tickers
# ------------------------------
if watchlist:
    st.divider()
    st.subheader("📈 Watchlist Analysis")

    if st.button("Analyze Watchlist"):
        with st.spinner("Analyzing tickers... please wait ⏳"):
            results = analyze_stocks(watchlist, period="1y")  # ensure enough data for SMA200

        rows = []
        for ticker, info in results.items():
            data = info.get("data")
            if data is not None and not data.empty:
                last_row = data.iloc[-1]
                close = last_row["Close"]
                sma50 = last_row["SMA50"]
                sma200 = last_row["SMA200"]
            else:
                close, sma50, sma200 = None, None, None

            rows.append({
                "Ticker": ticker,
                "Close": close,
                "50-MA": sma50,
                "200-MA": sma200,
                "Status": info["status"]
            })

        df = pd.DataFrame(rows)

        # Define color style for Status
        def color_status(val):
            if "Golden" in str(val):
                return "color: green; font-weight: bold;"
            elif "Death" in str(val):
                return "color: red; font-weight: bold;"
            elif "Insufficient" in str(val) or "Error" in str(val):
                return "color: white;"
            else:
                return "color: white;"

        styled_df = (
            df.style
            .map(color_status, subset=["Status"])
            .format({
                "Close": "{:.2f}",
                "50-MA": "{:.2f}",
                "200-MA": "{:.2f}"
            })
        )

        st.dataframe(styled_df, use_container_width=True)
