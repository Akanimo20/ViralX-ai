import os
import time
import random
from typing import Optional, Tuple

import streamlit as st
import pandas as pd
import requests

# --------------------------
# APP CONFIG (MUST BE FIRST Streamlit call)
# --------------------------
st.set_page_config(
    page_title="ViralX AI - Next-Gen X Growth Engine",
    layout="wide"
)

st.title("🚀 ViralX AI – The Only X Growth Tool You'll Ever Need in 2026+")

st.markdown("""
**Now with REAL X API integration** 🔥

Unique features no one else has:
- **Live X Trends** pulled directly from the X API
- **Real Profile Audits**
- **Data-Driven Virality Predictions**
- **Gamified Milestones**
- **Grok-Powered Content**
""")

# --------------------------
# Helper functions
# --------------------------
def get_api_key() -> Optional[str]:
    """
    Look up the X API key from Streamlit secrets or environment variables.
    Add your key to `.streamlit/secrets.toml`:
    [X]
    api_key = "your_key_here"

    Or set env var: export X_API_KEY="your_key_here"
    """
    # Try streamlit secrets first (recommended)
    try:
        key = st.secrets["X"]["api_key"]
        if key:
            return key
    except Exception:
        pass
    # Fallback to environment variable
    return os.getenv("X_API_KEY")


@st.cache_data(ttl=300)
def fetch_x_trends(query: str, max_results: int, api_key: str) -> Tuple[pd.DataFrame, dict]:
    """
    Fetch recent tweets for `query` using the X API v2 recent search endpoint.

    Returns:
        (DataFrame, headers_dict)
    """
    if not api_key:
        raise ValueError("Missing API key")
    if not query or not query.strip():
        raise ValueError("Query must not be empty")

    endpoint = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {api_key}"}
    # Ensure max_results is inside API bounds
    max_results = max(10, min(max_results, 100))

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username,name,verified",
    }

    max_attempts = 5
    backoff_base = 1.0

    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(endpoint, headers=headers, params=params, timeout=15)
        except requests.RequestException as e:
            last_exception = e
            sleep_for = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1)
            time.sleep(sleep_for)
            continue

        # If success, parse and return with headers
        if resp.status_code == 200:
            data = resp.json()
            tweets = data.get("data", [])
            includes = data.get("includes", {})
            users = includes.get("users", [])

            # map author_id -> username
            user_map = {u.get("id"): u.get("username") for u in users}

            rows = []
            for t in tweets:
                metrics = t.get("public_metrics", {}) or {}
                rows.append(
                    {
                        "id": t.get("id"),
                        "text": t.get("text"),
                        "author_id": t.get("author_id"),
                        "author_username": user_map.get(t.get("author_id")),
                        "created_at": t.get("created_at"),
                        "retweet_count": metrics.get("retweet_count"),
                        "reply_count": metrics.get("reply_count"),
                        "like_count": metrics.get("like_count"),
                        "quote_count": metrics.get("quote_count"),
                    }
                )

            df = pd.DataFrame(rows)
            # Return a plain dict of headers for UI consumption
            return df, dict(resp.headers)

        # Handle rate limiting
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after is not None else None
            except Exception:
                wait = None
            if wait and wait > 0:
                time.sleep(wait + random.uniform(0, 1))
            else:
                sleep_for = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1)
                time.sleep(sleep_for)
            last_exception = requests.HTTPError(f"429 rate limit: {resp.text}")
            continue

        # Retry on server errors (5xx)
        if 500 <= resp.status_code < 600:
            sleep_for = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1)
            time.sleep(sleep_for)
            last_exception = requests.HTTPError(f"{resp.status_code} server error: {resp.text}")
            continue

        # For client errors (4xx other than 429), raise immediately with details
        try:
            resp.raise_for_status()
        except requests.HTTPError as he:
            raise requests.HTTPError(f"X API returned error {resp.status_code}: {resp.text}") from he

    # If we exit loop, we failed after retries
    if last_exception:
        raise requests.HTTPError(f"Failed to fetch from X API after {max_attempts} attempts: {last_exception}")
    else:
        raise requests.HTTPError(f"Failed to fetch from X API after {max_attempts} attempts for unknown reasons")


def demo_trends_dataframe(query: str, max_results: int) -> pd.DataFrame:
    """
    Generate a small demo DataFrame for when the API key is not available or demo mode is selected.
    """
    max_results = max(5, min(max_results, 20))
    rows = []
    now = int(time.time())
    for i in range(max_results):
        rows.append(
            {
                "rank": i + 1,
                "sample_trend": f"{query} #{i+1}",
                "score": round(100 - i * 3 + (i % 3) * 1.5, 2),
                "example_text": f"Example post about {query} — generated demo #{i+1}",
                "fetched_at": pd.to_datetime(now - i * 60, unit="s"),
            }
        )
    return pd.DataFrame(rows)


# --------------------------
# Sidebar / Inputs
# --------------------------
st.sidebar.header("X API / Search")
query = st.sidebar.text_input("Search query or hashtag", value="#ai")
max_results = st.sidebar.number_input("Max results (demo)", min_value=5, max_value=100, value=10, step=5)
demo_mode = st.sidebar.checkbox("Demo mode (no API call)", value=False)

api_key = get_api_key()
if api_key:
    st.sidebar.success("X API key found")
else:
    st.sidebar.warning("No X API key found. Use demo mode or add your key to st.secrets or X_API_KEY env var.")

fetch_button = st.sidebar.button("Fetch Trends")

# --------------------------
# Main area: display results & rate-limit card
# --------------------------
if fetch_button:
    with st.spinner("Fetching trends..."):
        if demo_mode or not api_key:
            df = demo_trends_dataframe(query, max_results)
            headers = {}
            st.info("Showing demo data. Enable a valid X API key in st.secrets or as environment variable to fetch live data.")
            st.dataframe(df)
        else:
            try:
                df, headers = fetch_x_trends(query, max_results, api_key)
                if df.empty:
                    st.info("No results returned from the API for that query.")
                else:
                    st.dataframe(df)
            except ValueError as ve:
                headers = {}
                st.error(f"Configuration error: {ve}")
            except requests.HTTPError as he:
                headers = getattr(he, "response", {}) or {}
                st.error(f"Network/API error: {he}")
            except Exception as e:
                headers = {}
                st.error(f"Unexpected error: {e}")

        # Show rate-limit headers if available
        if headers:
            limit = headers.get("x-rate-limit-limit") or headers.get("X-Rate-Limit-Limit") or "N/A"
            remaining = headers.get("x-rate-limit-remaining") or headers.get("X-Rate-Limit-Remaining") or "N/A"
            reset = headers.get("x-rate-limit-reset") or headers.get("X-Rate-Limit-Reset")
            retry_after = headers.get("retry-after") or headers.get("Retry-After") or "N/A"

            col1, col2, col3 = st.columns(3)
            col1.metric("Rate limit", str(limit))
            col2.metric("Remaining", str(remaining))
            # Show reset time as minutes until reset if available
            if reset:
                try:
                    reset_ts = int(reset)
                    secs = max(0, reset_ts - int(time.time()))
                    mins = round(secs / 60, 2)
                    col3.metric("Reset (mins)", f"{mins}")
                except Exception:
                    col3.metric("Reset", str(reset))
            else:
                col3.metric("Reset", "N/A")

            if retry_after != "N/A":
                st.caption(f"Retry-After: {retry_after}")
else:
    st.markdown(
        "Use the sidebar to input a query and press 'Fetch Trends' to load results. "
        "Toggle 'Demo mode' to see example data without an API key."
    )

# --------------------------
# Footer / tips
# --------------------------
st.markdown("---")
st.caption(
    "Tip: add your X API credentials to `.streamlit/secrets.toml` or to the X_API_KEY environment variable. "
    "This implementation uses the X API v2 recent search endpoint and returns rate-limit headers for visibility."
)