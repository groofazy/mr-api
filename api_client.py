import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import urllib.parse

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