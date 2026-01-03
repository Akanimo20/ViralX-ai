import streamlit as st
import pandas as pd
import requests

# App config (must be first Streamlit call)
st.set_page_config(page_title="ViralX AI - X Growth Tool 2026", layout="wide")

st.title("🚀 ViralX AI - Your X Growth Engine (2026 Edition)")

st.markdown("""
**Real X API integration - Working in 2026** 🔥

Features:
- Load your profile & followers count
- Fetch and **save post history** automatically (deduplicated)
- Engagement stats from your real posts
- Live global trends
- Grok-powered content suggestions (real if you add key)
""")

# Sidebar for API keys
st.sidebar.header("🔑 API Keys")

st.sidebar.markdown("**X Bearer Token** (App-only):")
bearer_token = st.sidebar.text_input("Bearer Token", type="password")
if bearer_token:
    st.session_state.bearer_token = bearer_token

st.sidebar.markdown("**Grok API Key** (Optional):")
grok_key = st.sidebar.text_input("Grok Key", type="password")
if grok_key:
    st.session_state.grok_key = grok_key

# Session state
if "posts_history" not in st.session_state:
    st.session_state.posts_history = []

# ---------------- Helper Functions ---------------- #

def call_grok(prompt: str) -> str:
    if st.session_state.get("grok_key"):
        try:
            headers = {
                "Authorization": f"Bearer {st.session_state.grok_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
            }
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            st.error("Grok API failed — using mock response")

    return f"Mock Grok response:\n\nOptimized thread ideas for:\n{prompt}"


def get_profile(username: str):
    token = st.session_state.get("bearer_token")
    if not token or not username:
        return None

    clean = username.lstrip("@")
    url = f"https://api.x.com/2/users/by/username/{clean}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"user.fields": "public_metrics,description"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("data")
    except Exception:
        pass

    return None


def get_posts(user_id: str):
    token = st.session_state.get("bearer_token")
    if not token:
        return []

    url = f"https://api.x.com/2/users/{user_id}/tweets"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "tweet.fields": "public_metrics,created_at,text",
        "exclude": "replies,retweets",
        "max_results": 100,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("data", [])
    except Exception:
        pass

    return []


def get_trends():
    token = st.session_state.get("bearer_token")
    if not token:
        return []

    url = "https://api.twitter.com/1.1/trends/place.json"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"id": 1}  # Global

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()[0].get("trends", [])[:20]
    except Exception:
        pass

    return []

# ---------------- Main App ---------------- #

if st.session_state.get("bearer_token"):
    username = st.text_input("Your X username (with or without @)")

    if st.button("Load Profile & Save Posts"):
        if not username:
            st.warning("Please enter a username")
        else:
            with st.spinner("Fetching profile & posts..."):
                profile = get_profile(username)

                if profile:
                    metrics = profile.get("public_metrics", {})
                    followers = metrics.get("followers_count", 0)

                    st.success(f"@{profile['username']} — {followers:,} followers")

                    posts = get_posts(profile["id"])

                    if posts:
                        existing_ids = {p["id"] for p in st.session_state.posts_history}
                        new_posts = [p for p in posts if p["id"] not in existing_ids]
                        st.session_state.posts_history.extend(new_posts)

                        st.info(
                            f"Added {len(new_posts)} new posts "
                            f"(Total: {len(st.session_state.posts_history)})"
                        )

                        df = pd.DataFrame(st.session_state.posts_history)

                        df["engagement"] = df["public_metrics"].apply(
                            lambda x: (
                                x.get("like_count", 0)
                                + x.get("retweet_count", 0)
                                + x.get("reply_count", 0)
                            )
                        )

                        st.metric(
                            "Average Engagement per Post",
                            f"{df['engagement'].mean():.0f}",
                        )

                        display_df = df[["created_at", "text", "engagement"]].copy()
                        display_df["created_at"] = pd.to_datetime(
                            display_df["created_at"]
                        ).dt.strftime("%Y-%m-%d")

                        st.dataframe(
                            display_df.sort_values("created_at", ascending=False),
                            use_container_width=True,
                        )
                    else:
                        st.warning("No posts found")
                else:
                    st.error("Profile not found or invalid token")

    st.header("🌍 Live Global Trends")
    trends = get_trends()

    if trends:
        trends_df = pd.DataFrame(trends)
        if "tweet_volume" not in trends_df:
            trends_df["tweet_volume"] = None
        st.table(trends_df[["name", "tweet_volume"]])
    else:
        st.info("No trends available (token tier or endpoint restriction)")

    st.header("🧠 Grok Content Ideas")
    prompt = st.text_area(
        "Prompt",
        value="Suggest 3 viral X threads based on growth & AI niche",
        height=150,
    )

    if st.button("Generate"):
        with st.spinner("Grok thinking..."):
            st.markdown(call_grok(prompt))

else:
    st.info("Enter your X Bearer Token in the sidebar to unlock all features.")

st.caption("ViralX AI — 2026 X API Ready • Post history saved automatically")
