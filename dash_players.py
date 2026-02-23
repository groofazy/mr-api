import streamlit as st
import api_client
import pandas as pd
import altair as alt
import json
import time
from typing import Any

st.set_page_config(page_title="Marvel Rivals — Player Explorer", layout="wide")
st.title("Marvel Rivals — Player Explorer")

# Load API key (api_client does the same load; we call for a presence check)
api_key = api_client._load_api_key()
if not api_key:
    st.error("API key not found. Put MARVEL_RIVALS_API_KEY in .env.local next to the repo files.")
    st.stop()

# Cached API wrappers
@st.cache_data(ttl=300)
def search_player_cached(query: str):
    return api_client.search_player(query, api_key=api_key)

@st.cache_data(ttl=300)
def get_player_cached(player_id: str):
    return api_client.fetch_player_by_id(player_id, api_key=api_key)

@st.cache_data(ttl=300)
def get_player_stats_cached(player_id: str):
    return api_client.fetch_player_stats_v2(player_id, api_key=api_key)

# Sidebar: search with cooldown handling
st.sidebar.header("Find a player")

# session cooldown state
if "player_search_cooldown_until" not in st.session_state:
    st.session_state["player_search_cooldown_until"] = 0.0

cooldown_remaining = max(0, st.session_state["player_search_cooldown_until"] - time.time())

query = st.sidebar.text_input("Player name or ID", key="player_search_input")

# show cooldown and disable search button when active
if cooldown_remaining > 0:
    st.sidebar.write(f"Rate limit cooldown: wait {int(cooldown_remaining)}s")
    search_btn = st.sidebar.button("Search", key="player_search_btn", disabled=True)
else:
    search_btn = st.sidebar.button("Search", key="player_search_btn", disabled=False)

search_results = []
if search_btn and query:
    res = search_player_cached(query)
    # If api_client returned a rate-limit (429) include retry metadata
    if isinstance(res, dict) and res.get("_error"):
        status = res.get("status")
        retry_after = res.get("retry_after") or None
        text = (res.get("text") or "").lower() if isinstance(res.get("text"), str) else ""
        if status == 429 or "too many requests" in text:
            cooldown_seconds = int(retry_after) if retry_after else 10
            st.session_state["player_search_cooldown_until"] = time.time() + cooldown_seconds
            st.sidebar.warning(f"Rate limited by API. Cooling down for {cooldown_seconds} seconds.")
        else:
            st.sidebar.warning(f"Search failed: {res.get('text') or res.get('reason') or res.get('status')}")
    else:
        search_results = res if isinstance(res, list) else []

# If no explicit search was done, optionally show recent search placeholder
if not search_results and not search_btn:
    st.sidebar.info("Enter a name or ID and click Search")

# If we have results, show them in a selectbox
selected_player = None
if search_results:
    # build labels and maintain mapping
    def player_label(p):
        pid = p.get("id") or p.get("player_id") or p.get("account_id") or ""
        name = p.get("name") or p.get("username") or p.get("displayName") or p.get("player_name") or ""
        platform = p.get("platform") or p.get("region") or ""
        label = f"{name} ({pid})" if pid else name
        if platform:
            label = f"{label} [{platform}]"
        return label

    labels = [player_label(p) for p in search_results]
    sel = st.sidebar.selectbox("Search results", options=labels, key="player_results_select")
    selected_player = search_results[labels.index(sel)]

# Optionally allow direct ID entry to load a player
if not selected_player:
    direct_id = st.sidebar.text_input("Or enter player ID directly", key="player_direct_id")
    if direct_id:
        p = get_player_cached(direct_id)
        if isinstance(p, dict) and p.get("_error"):
            st.sidebar.warning(f"Could not fetch player {direct_id}: {p.get('text') or p.get('reason')}")
        else:
            selected_player = p if isinstance(p, dict) else (p[0] if isinstance(p, list) and p else None)

# If still not selected, stop
if not selected_player:
    st.info("No player selected. Search for a player in the sidebar to begin.")
    st.stop()

# Display player header info
player_id = selected_player.get("id") or selected_player.get("player_id") or selected_player.get("account_id") or ""
player_name = selected_player.get("name") or selected_player.get("username") or selected_player.get("displayName") or selected_player.get("player_name") or "Unknown"

st.header(f"Player: {player_name}")
st.markdown(f"**ID:** {player_id}")
if selected_player.get("platform"):
    st.markdown(f"**Platform:** {selected_player.get('platform')}")
if selected_player.get("region"):
    st.markdown(f"**Region:** {selected_player.get('region')}")
if selected_player.get("created_at"):
    st.markdown(f"**Joined:** {selected_player.get('created_at')}")

# Main layout: left details, right analytics
left, right = st.columns([1, 2])

with left:
    st.subheader("Profile JSON")
    st.json(selected_player)

    # quick top-level metrics if present on the profile object
    st.subheader("Quick metrics")
    metrics = []
    for k in ("level", "matches_played", "wins", "losses", "win_rate"):
        if k in selected_player:
            metrics.append((k, selected_player[k]))
    if metrics:
        cols = st.columns(len(metrics))
        for col, (k, v) in zip(cols, metrics):
            with col:
                st.metric(label=k.replace("_", " ").title(), value=str(v))

with right:
    st.subheader("Player Stats & Analytics")
    stats = get_player_stats_cached(player_id)
    if not stats or (isinstance(stats, dict) and stats.get("_error")):
        st.warning("Could not fetch player stats.")
        if isinstance(stats, dict):
            st.write(stats.get("text") or stats.get("reason"))
    else:
        # Stats rendering: intelligently find structures we can chart
        def is_number_like(x):
            try:
                if isinstance(x, bool):
                    return False
                float(x)
                return True
            except Exception:
                return False

        # Attempt to find hero usage keys
        hero_usage = None
        for candidate in ("heroes", "hero_usage", "top_heroes", "heroes_played"):
            if candidate in stats and isinstance(stats[candidate], (list, dict)):
                hero_usage = stats[candidate]
                break

        if hero_usage:
            st.markdown("### Top heroes")
            # Normalize hero_usage into a DataFrame with columns: hero, value
            if isinstance(hero_usage, dict):
                rows = []
                for name, val in hero_usage.items():
                    rows.append({"hero": name, "value": val})
                df_heroes = pd.DataFrame(rows)
            else:
                df_heroes = pd.DataFrame(hero_usage)
                if "name" not in df_heroes.columns:
                    for col in ("hero", "title", "name_display"):
                        if col in df_heroes.columns:
                            df_heroes = df_heroes.rename(columns={col: "hero"})
                            break
                if "value" not in df_heroes.columns:
                    for col in ("plays", "count", "usage", "games"):
                        if col in df_heroes.columns:
                            df_heroes = df_heroes.rename(columns={col: "value"})
                            break
            if "value" in df_heroes.columns:
                df_heroes["value"] = pd.to_numeric(df_heroes["value"], errors="coerce").fillna(0)
            else:
                df_heroes["value"] = 1

            df_heroes = df_heroes.sort_values("value", ascending=False).head(12)
            if not df_heroes.empty:
                chart = alt.Chart(df_heroes).mark_bar().encode(
                    x=alt.X("value:Q", title="Plays / Value"),
                    y=alt.Y("hero:N", sort='-x', title="Hero"),
                    tooltip=["hero:N", "value:Q"]
                ).properties(height=400)
                st.altair_chart(chart, use_container_width=True)
                # ensure 'hero' and 'value' are safe types for st.table
                display_df = df_heroes[["hero", "value"]].reset_index(drop=True)
                display_df["hero"] = display_df["hero"].astype(str)
                st.table(display_df)

        # Numeric summary: find top-level numeric keys
        numeric_items = []
        other_items = {}

        if isinstance(stats, dict):
            for k, v in stats.items():
                if is_number_like(v):
                    numeric_items.append((k, float(v)))
                else:
                    other_items[k] = v

        # Show top numeric metrics
        if numeric_items:
            st.markdown("### Key metrics")
            top_metrics = numeric_items[:4]
            cols = st.columns(len(top_metrics))
            for col, (k, v) in zip(cols, top_metrics):
                with col:
                    st.metric(label=k.replace("_", " ").title(), value=str(v))

            df_nums = pd.DataFrame([{"metric": k, "value": v} for k, v in numeric_items])
            df_nums = df_nums.sort_values("value", ascending=False).head(12)
            if not df_nums.empty:
                chart = alt.Chart(df_nums).mark_bar().encode(
                    x=alt.X("value:Q", title="Value"),
                    y=alt.Y("metric:N", sort='-x', title="Metric"),
                    tooltip=["metric:N", "value:Q"]
                ).properties(height=350)
                st.altair_chart(chart, use_container_width=True)

        # Attempt to render a time series if present (pick first candidate)
        ts_candidate = None
        if isinstance(stats, dict):
            for k, v in stats.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    # heuristic: if any dict in list contains a time-like key and a numeric
                    keys = set().union(*(d.keys() for d in v if isinstance(d, dict)))
                    if any(t in name.lower() for name in keys for t in ("time", "date", "timestamp")):
                        ts_candidate = (k, v)
                        break

        if ts_candidate:
            ts_key, ts_data = ts_candidate
            st.markdown(f"### Time series: {ts_key}")
            try:
                df_ts = pd.DataFrame(ts_data)
                ts_col = None
                for c in df_ts.columns:
                    if "time" in c.lower() or "date" in c.lower() or "timestamp" in c.lower():
                        ts_col = c
                        break
                val_col = None
                for c in df_ts.columns:
                    if c == ts_col:
                        continue
                    if df_ts[c].apply(lambda x: is_number_like(x)).any():
                        val_col = c
                        break
                if ts_col and val_col:
                    df_ts[ts_col] = pd.to_datetime(df_ts[ts_col], errors="coerce")
                    df_ts[val_col] = pd.to_numeric(df_ts[val_col], errors="coerce")
                    df_ts = df_ts.dropna(subset=[ts_col, val_col])
                    line = alt.Chart(df_ts).mark_line(point=True).encode(
                        x=alt.X(f"{ts_col}:T", title=ts_col),
                        y=alt.Y(f"{val_col}:Q", title=val_col),
                        tooltip=[f"{ts_col}:T", f"{val_col}:Q"]
                    ).interactive().properties(height=350)
                    st.altair_chart(line, use_container_width=True)
                else:
                    st.write("Time series exists but format isn't recognized. Showing raw JSON:")
                    st.json(ts_data)
            except Exception as e:
                st.write("Could not render time-series chart:", e)
                st.json(ts_data)

        # Other details & raw JSON
        st.markdown("### Other details")
        for k, v in other_items.items():
            with st.expander(k):
                if isinstance(v, (dict, list)):
                    st.json(v)
                else:
                    st.write(v)

        st.subheader("Full stats JSON")
        st.json(stats)

# Footer/context
st.caption("Data from Marvel Rivals API. Make sure MARVEL_RIVALS_API_KEY is set in .env.local.")