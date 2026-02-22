import requests
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("MARVEL_RIVALS_API_KEY")
BASE_URL = "https://marvelrivalsapi.com/api/v1"


HEADERS = {
    "x-api-key": API_KEY
}

def get_endpoint(endpoint: str):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        print("Unauthorized - check your API key")
    else:
        print(f"Error {response.status_code}: {response.text}")
    
    return None

def test_endpoint(response):
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        print("Unauthorized - check your API key")
    else:
        print(f"Error {response.status_code}: {response.text}")
    
    return None


def get_hero_stats(query: str):
    url = f"{BASE_URL}/heroes/hero/{query}/stats"
    response = requests.get(url, headers=HEADERS)

    test_endpoint(response)



# Example: get maps
ironman = get_hero_stats("ironman")
print(ironman)