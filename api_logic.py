import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import json

env_path = Path(__file__).resolve().parent / ".env.local"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("MARVEL_RIVALS_API_KEY")
BASE_URL = "https://marvelrivalsapi.com/api/v1"


HEADERS = {
    "x-api-key": API_KEY
}

def test_endpoint(response):
    if response is None:
        print("No response object provided.")
        return 
    
    if response.status_code == 200:
        print("OK (200) - response received.")
    elif response.status_code == 401:
        print("Unauthorized - check your API key")
    else:
        print(f"Error {response.status_code}: {response.text}")

def list_heroes():
    url = f"{BASE_URL}/heroes"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        test_endpoint(response)
        return None

def print_hero_stats(dict):

    hero_id = dict["hero_id"]
    print(f"Hero ID: {hero_id}")

    hero_name = dict["hero_name"]
    print(f"Hero Name: {hero_name}")

def search_player(query: str):
    url = f"{BASE_URL}/find-player/{query}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json
    else:
        test_endpoint(response)
        return None

def get_hero_stats(query: str):
    url = f"{BASE_URL}/heroes/hero/{query}/stats"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        test_endpoint(response)
        return None

def test_get_hero_stats():
    test_hero = "iron man"
    result = get_hero_stats(test_hero)
    print(result)
    print_hero_stats(result)

# test_get_hero_stats()

def get_player_creds(query: str):
    url = f"{BASE_URL}/find-player/{query}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        test_endpoint(response)
        return None

def test_get_player_creds():
    test_user = "keuandhsk"
    result = get_player_creds(test_user)

    print(result)

def get_player_stats(query: str):
    url = f"{BASE_URL}/player/{query}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        test_endpoint(response)
        return None

def test_get_player_stats():
    test_user = "jerraaa"
    result = get_player_stats(test_user)
    print(result)
    return result

def return_match_history():
    player_stats = test_get_player_stats()
    match_history = player_stats["match_history"]
    print(match_history)
    return match_history

def print_match_history():
    match_history = return_match_history()
    print("Matches: ", len(match_history))
    if match_history:
        df = match


def test_suite():
    # test_get_hero_stats()
    # test_get_player_creds()
    # test_get_player_stats()

    return_match_history()

test_suite()