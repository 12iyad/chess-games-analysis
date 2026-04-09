import requests
import chess

username = "12iyad"
url = f"https://api.chess.com/pub/player/{username}/games/archives"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
response = requests.get(url, headers=headers)

if not response.ok:
    print(f"Request failed: {response.status_code}")
    print(response.text[:500] if response.text else "(empty response)")
else:
    data = response.json()
    print(data)
