import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import urllib.parse
from typing import Any

# Defaults
BASE_URL = "https://marvelrivalsapi.com/api/v1"
DEFAULT_ENV_FILE = ".env.local"

def _load_api_key(env_path: Path | None = None) -> str | None:
    """
    Load MARVEL_RIVALS_API_KEY from .env.local (or .env) in the same folder as this file
    or from an explicitly provided Path.
    """
    if env_path is None:
        env_path = Path(__file__).resolve().parent / DEFAULT_ENV_FILE
    load_dotenv(dotenv_path=env_path)
    return os.getenv("MARVEL_RIVALS_API_KEY")

def _headers(api_key: str | None) -> dict:
    if not api_key:
        return {}
    return {"x-api-key": api_key}

def _normalize_heroes_payload(data):
    """
    Return a list of hero dicts for common response shapes:
    - top-level list
    - wrapper dict with keys like "data" / "results" / "heroes"
    - mapping id -> hero object
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "results", "heroes", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # fallback: dict mapping id -> object
        if all(isinstance(v, dict) for v in data.values()):
            items = []
            for k, v in data.items():
                obj = dict(v)
                if "id" not in obj:
                    obj["id"] = k
                items.append(obj)
            return items
    return []

def fetch_heroes(api_key: str | None = None, env_path: Path | None = None):
    """
    Fetch /heroes. Returns a list of hero dicts on success,
    or a dict with _error information on failure.
    """
    if api_key is None:
        api_key = _load_api_key(env_path)
    headers = _headers(api_key)
    if not headers:
        return {"_error": True, "reason": "missing_api_key"}

    url = f"{BASE_URL}/heroes"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return _normalize_heroes_payload(r.json())
    return {"_error": True, "status": r.status_code, "text": r.text}

def fetch_hero_stats(identifier: str, api_key: str | None = None, env_path: Path | None = None):
    """
    Fetch /heroes/hero/{identifier}/stats. Returns parsed JSON on success,
    or dict with _error info on failure.
    """
    if api_key is None:
        api_key = _load_api_key(env_path)
    headers = _headers(api_key)
    if not headers:
        return {"_error": True, "reason": "missing_api_key"}

    q = urllib.parse.quote_plus(str(identifier))
    url = f"{BASE_URL}/heroes/hero/{q}/stats"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return {"_error": True, "status": r.status_code, "text": r.text}

# --------------------
# New: Player helpers (search + v2 stats)
# --------------------
def _safe_get(url: str, headers: dict, timeout: int = 15) -> Any:
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        return r
    except Exception as e:
        return {"_error": True, "reason": f"request_failed: {e}"}

def _try_endpoints(endpoints: list, headers: dict) -> Any:
    """
    Try a list of endpoint URLs, return the first successful parsed JSON (200),
    or an error dict describing the last response.

    Detects HTTP 429 (rate limit) and returns a dict containing "status": 429
    and "retry_after" (seconds) when the API provides a Retry-After header.
    This avoids sleeping in the client and lets the UI implement a non-blocking cooldown.
    """
    last_resp = None
    for url in endpoints:
        r = _safe_get(url, headers)
        last_resp = r
        if isinstance(r, dict) and r.get("_error"):
            # network error: stop and return it
            return r

        status = getattr(r, "status_code", None)

        if status == 200:
            try:
                return r.json()
            except Exception:
                return {"_error": True, "status": 200, "text": r.text}

        # Rate limit: prefer server Retry-After header if present
        if status == 429:
            retry_after = None
            try:
                # some servers return seconds, some return HTTP-date — prefer integer seconds when possible
                ra = r.headers.get("Retry-After")
                if ra is not None:
                    retry_after = int(ra)
            except Exception:
                retry_after = None
            return {"_error": True, "status": 429, "text": r.text, "retry_after": retry_after, "headers": dict(r.headers)}

        # For other non-200 responses, continue to next candidate endpoint
    # none succeeded
    if isinstance(last_resp, requests.Response):
        return {"_error": True, "status": last_resp.status_code, "text": last_resp.text, "headers": dict(last_resp.headers)}
    return {"_error": True, "reason": "no_endpoints_succeeded"}

def search_player(query: str, api_key: str | None = None, env_path: Path | None = None):
    """
    Try to find players using the query (name / id). Returns list of matches or error dict.
    """
    if api_key is None:
        api_key = _load_api_key(env_path)
    headers = _headers(api_key)
    if not headers:
        return {"_error": True, "reason": "missing_api_key"}

    q = urllib.parse.quote_plus(str(query))
    candidates = [
        f"{BASE_URL}/players/search?name={q}",
        f"{BASE_URL}/players/search?q={q}",
        f"{BASE_URL}/search/player?name={q}",
        f"{BASE_URL}/search/player?q={q}",
        f"{BASE_URL}/players?search={q}",
        f"{BASE_URL}/player/search?name={q}",
        f"{BASE_URL}/player/search?q={q}",
    ]
    res = _try_endpoints(candidates, headers)
    # normalize responses: return list if top-level list, or try wrapper keys
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for k in ("data", "results", "players", "items"):
            if k in res and isinstance(res[k], list):
                return res[k]
        # sometimes search returns single object
        if "id" in res and isinstance(res.get("id"), (str, int)):
            return [res]
    return {"_error": True, "status": res.get("status") if isinstance(res, dict) else None, "text": res.get("text") if isinstance(res, dict) else str(res)}

def fetch_player_by_id(player_id: str, api_key: str | None = None, env_path: Path | None = None):
    """
    Fetch basic player object by id (tries multiple endpoint shapes).
    """
    if api_key is None:
        api_key = _load_api_key(env_path)
    headers = _headers(api_key)
    if not headers:
        return {"_error": True, "reason": "missing_api_key"}

    q = urllib.parse.quote_plus(str(player_id))
    candidates = [
        f"{BASE_URL}/players/{q}",
        f"{BASE_URL}/player/{q}",
        f"{BASE_URL}/player?id={q}",
    ]
    return _try_endpoints(candidates, headers)

def fetch_player_stats_v2(player_id: str, api_key: str | None = None, env_path: Path | None = None):
    """
    Fetch v2 player stats. Tries a few likely endpoint forms used by the docs.
    Returns parsed JSON or error dict.
    """
    if api_key is None:
        api_key = _load_api_key(env_path)
    headers = _headers(api_key)
    if not headers:
        return {"_error": True, "reason": "missing_api_key"}

    q = urllib.parse.quote_plus(str(player_id))
    candidates = [
        f"{BASE_URL}/player/{q}/stats/v2",
        f"{BASE_URL}/players/{q}/stats/v2",
        f"{BASE_URL}/player/stats/v2/{q}",
        f"{BASE_URL}/player/{q}/stats",
        f"{BASE_URL}/players/{q}/stats",
    ]
    return _try_endpoints(candidates, headers)