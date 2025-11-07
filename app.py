import streamlit as st
import pandas as pd
from cross_alert import analyze_stocks, search_ticker
import firebase_admin
from firebase_admin import credentials, firestore

# ------------------------------
# Page setup
# ------------------------------
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
# Logging helper
# ------------------------------
def log(message):
    """Append message to session_state log and display in Streamlit."""
    if "log_area" not in st.session_state:
        st.session_state["log_area"] = []
    st.session_state["log_area"].append(str(message))
    st.write(str(message))  # Show in UI

# ------------------------------
# Load watchlist from Firestore
# ------------------------------
def get_watchlist():
    try:
        docs = db.collection("watchlist").stream()
        watchlist = [doc.to_dict()["symbol"] for doc in docs]
        log(f"✅ Loaded watchlist: {watchlist}")
        return watchlist
    except Exception as e:
        log(f"❌ Error loading watchlist: {e}")
        return []

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
                try:
                    db.collection("watchlist").add({"symbol": ticker})
                    st.success(f"✅ {ticker} added to watchlist!")
                    watchlist.append(ticker)
                    log(f"✅ {ticker} added to Firebase watchlist")
                except Exception as e:
                    st.error(f"❌ Failed to add {ticker}: {e}")
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
            try:
                docs = db.collection("watchlist").where("symbol", "==", remove_ticker).stream()
                for doc in docs:
                    doc.reference.delete()
                watchlist.remove(remove_ticker)
                st.warning(f"❌ {remove_ticker} removed from watchlist.")
                log(f"❌ {remove_ticker} removed from Firebase")
            except Exception as e:
                st.error(f"❌ Failed to remove {remove_ticker}: {e}")
else:
    st.info("Your watchlist is empty. Add some tickers above 👆")

# ------------------------------
# Analyze tickers
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
        analyze_stocks.clear()
        search_ticker.clear()
        st.success("✅ Cache cleared — next analysis will fetch fresh data")
        log("🔄 Cache cleared")

    if analyze_clicked:
        with st.spinner("Analyzing tickers... please wait ⏳"):
            try:
                results = analyze_stocks(watchlist, period="2y", interval="1d")
                log(f"✅ Analysis completed for tickers: {list(results.keys())}")
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                log(f"❌ Analysis error: {e}")
                results = {}

        rows = []
        for ticker, info in results.items():
            data = info.get("data")
            if data is not None and not data.empty:
                last_row = data.iloc[-1]
                close = last_row.get("Close", None)
                sma50 = last_row.get("SMA50", None)
                sma200 = last_row.get("SMA200", None)
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

# ------------------------------
# Debug Logs Panel
# ------------------------------
st.subheader("📝 Debug Logs")
if st.session_state.get("log_area"):
    for msg in st.session_state["log_area"]:
        st.text(msg)
