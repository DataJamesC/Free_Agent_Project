import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: FREEAGENT_CLIENT_ID or FREEAGENT_CLIENT_SECRET missing from .env")
    exit(1)

# Prompt interactively so no code is ever saved to disk
auth_code = input("Paste the 'code' parameter from your browser URL: ").strip()

url = "https://api.sandbox.freeagent.com/v2/token_endpoint"

payload = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": "http://localhost:8080/callback",
}

response = requests.post(
    url,
    data=payload,
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={"Accept": "application/json"},
)

if response.status_code == 200:
    data = response.json()
    print("\n Success! Add this line to your .env file:\n")
    print(f'FREEAGENT_REFRESH_TOKEN="{data.get("refresh_token")}"')
else:
    print(f"\n Error {response.status_code}: {response.text}")