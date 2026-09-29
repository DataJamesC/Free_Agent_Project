# Extract Invoices from FreeAgent API v2
# Docs: https://dev.freeagent.com/docs/invoices

import json
import os
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("FREEAGENT_REFRESH_TOKEN")

# Step 1: Refresh OAuth access token
token_url = "https://api.sandbox.freeagent.com/v2/token_endpoint"
token_response = requests.post(
    token_url,
    data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={"Accept": "application/json"},
)

if token_response.status_code != 200:
    print(
        f"Auth Error {token_response.status_code}: {token_response.text}"
    )
    exit(1)

access_token = token_response.json()["access_token"]

# Step 2: Set parameters (Invoices updated in last 3 days)
three_days_ago = datetime.now() - timedelta(days=3)
updated_since = three_days_ago.strftime("%Y-%m-%dT00:00:00.000Z")

url = "https://api.sandbox.freeagent.com/v2/invoices"
params = {"updated_since": updated_since, "view": "all", "per_page": 100}

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

# Step 3: Fetch data
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    records = data.get("invoices", [])
    print(f"Invoices retrieved successfully. Count: {len(records)}")

    # Ensure output folder exists and save JSON
    os.makedirs("data", exist_ok=True)
    with open("data/raw_invoices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
else:
    print(f"Error {response.status_code}: {response.text}")