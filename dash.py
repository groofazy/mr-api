import streamlit as st
import api_client
import urllib.parse
import pandas as pd
import json

st.set_page_config(page_title="Marvel Rivals — Hero Stats", layout="wide")
st.title("Marvel Rivals — Hero Stats")

# Read API key using api_client loader (it checks .env.local next to api_client)
api_key = api_client._load_api_key()
if not api_key:
    st.error("API key not found. Put MARVEL_RIVALS_API_KEY in .env.local next to the repo files.")
    st.stop()

HEADERS = {"x-api-key": api_key}
BASE_IMAGE_URL = "https://marvelrivalsapi.com"

@st.cache_data(ttl=300)
def get_heroes_cached():
    return api_client.fetch_heroes(api_key=api_key)

@st.cache_data(ttl=300)
def get_stats_cached(identifier: str):
    return api_client.fetch_hero_stats(identifier, api_key=api_key)

heroes = get_heroes_cached()
if not heroes:
    st.info("No heroes available or fetch failed.")
    st.stop()

def hero_label(h):
    name = h.get("name") or h.get("hero_name") or h.get("slug") or h.get("id") or "unknown"
    hid = h.get("id") or h.get("hero_id") or ""
    return f"{name} ({hid})" if hid else name

hero_map = {hero_label(h): h for h in heroes}
labels = sorted(list(hero_map.keys()), key=lambda s: s.lower())

search = st.sidebar.text_input("Search heroes")
if search:
    labels = [l for l in labels if search.lower() in l.lower()]

selected = st.sidebar.selectbox("Select hero", labels)
hero = hero_map[selected]

# Display hero info
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Hero Info")
    st.markdown(f"**ID:** {hero.get('id') or hero.get('hero_id','')}")
    st.markdown(f"**Name:** {hero.get('name') or hero.get('hero_name','')}")
    st.markdown(f"**Role:** {hero.get('role','')}")
    st.markdown(f"**Attack type:** {hero.get('attack_type','')}")
    img = hero.get("imageUrl") or hero.get("image") or ""
    if img:
        if img.startswith("/"):
            img_url = BASE_IMAGE_URL + img
        elif img.startswith("http"):
            img_url = img
        else:
            img_url = BASE_IMAGE_URL + "/" + img.lstrip("/")
        st.image(img_url, width=300)

# with col2:
#     st.subheader("Hero JSON")
#     st.json(hero)

with st.expander("Stats"):
    identifier = hero.get("id") or hero.get("slug") or hero.get("name")
    stats = get_stats_cached(identifier)
    if not stats or stats.get("_error"):
        st.warning(f"Could not fetch stats (status: {stats.get('status') if isinstance(stats, dict) else 'unknown'})")
        if isinstance(stats, dict):
            st.write(stats.get("text") or stats.get("reason"))
    else:
        if isinstance(stats, dict):
            # helpers
            def is_numeric_like(x):
                try:
                    # treat booleans separately (they're not numeric for metrics)
                    if isinstance(x, bool):
                        return False
                    float(x)
                    return True
                except Exception:
                    return False

            def chunk_list(lst, n):
                for i in range(0, len(lst), n):
                    yield lst[i:i+n]

            # split stats into numeric and others
            numeric_stats = []
            short_text_stats = []
            long_or_complex_stats = {}

            for k, v in stats.items():
                # ignore obvious metadata keys if needed (optional)
                # if k in ("_meta",): continue

                if isinstance(v, (int, float)) or (isinstance(v, str) and is_numeric_like(v)):
                    numeric_stats.append((k, v))
                elif isinstance(v, (dict, list)) or (isinstance(v, str) and len(v) > 120):
                    long_or_complex_stats[k] = v
                else:
                    # short strings, booleans, small things
                    short_text_stats.append((k, v))

            # Numeric metrics grid (use 3 columns by default)
            if numeric_stats:
                st.markdown("#### Key numeric stats")
                cols_per_row = 3
                for row in chunk_list(numeric_stats, cols_per_row):
                    cols = st.columns(len(row))
                    for col, (k, v) in zip(cols, row):
                        with col:
                            # st.metric expects label and value (value as string/number)
                            # convert numeric strings to a nicer numeric presentation
                            display_value = float(v) if is_numeric_like(v) else v
                            # Round floats for display (optional)
                            if isinstance(display_value, float):
                                # show as integer when it looks integral
                                if display_value.is_integer():
                                    display_value = int(display_value)
                                else:
                                    display_value = round(display_value, 2)
                            st.metric(label=k, value=display_value)

            # Short text/boolean stats as thin boxes
            if short_text_stats:
                st.markdown("#### Quick stats")
                cols_per_row = 2
                for row in chunk_list(short_text_stats, cols_per_row):
                    cols = st.columns(len(row))
                    for col, (k, v) in zip(cols, row):
                        with col:
                            # small box using st.info
                            st.info(f"**{k}**\n\n{v}")

            # Long or complex stats in expanders (JSON for dicts/lists)
            if long_or_complex_stats:
                st.markdown("#### Detailed / complex stats")
                for k, v in long_or_complex_stats.items():
                    with st.expander(k):
                        if isinstance(v, (dict, list)):
                            st.json(v)
                        else:
                            st.write(v)

            # Full raw JSON at the end for debugging
            st.subheader("Full stats JSON")
            st.json(stats)

        else:
            st.write(stats)

st.sidebar.caption("Data: Marvel Rivals API")