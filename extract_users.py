# Extract ALL Users (Employee Dimension) with Pagination from FreeAgent API v2
# Docs: https://dev.freeagent.com/docs/users

import json
import os
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
    print(f"Auth Error {token_response.status_code}: {token_response.text}")
    exit(1)

access_token = token_response.json()["access_token"]

# Step 2: Setup Paginated Extraction Loop
url = "https://api.sandbox.freeagent.com/v2/users"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

all_users = []
page = 1
per_page = 100

print("Starting paginated users extraction...")

while True:
    params = {
        "view": "all",
        "page": page,
        "per_page": per_page,
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        print(f"Error on page {page} ({response.status_code}): {response.text}")
        break

    data = response.json()
    users_batch = data.get("users", [])

    if not users_batch:
        break

    all_users.extend(users_batch)
    print(f"Page {page}: Fetched {len(users_batch)} users (Total: {len(all_users)})")

    if len(users_batch) < per_page:
        break

    page += 1

# Step 3: Save all extracted records
os.makedirs("data", exist_ok=True)
output_path = "data/raw_users.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"users": all_users}, f, indent=2)

print(f"\nExtraction complete! Saved {len(all_users)} users to {output_path}")