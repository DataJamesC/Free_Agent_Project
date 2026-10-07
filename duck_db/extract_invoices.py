# Extract ALL Invoices with Pagination from FreeAgent API v2
# Docs: https://dev.freeagent.com/docs/invoices

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
url = "https://api.sandbox.freeagent.com/v2/invoices"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

all_invoices = []
page = 1
per_page = 100

print("Starting paginated invoice extraction...")

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
    invoices_batch = data.get("invoices", [])

    # Exit loop if no records are returned
    if not invoices_batch:
        break

    all_invoices.extend(invoices_batch)
    print(f"Page {page}: Fetched {len(invoices_batch)} invoices (Total: {len(all_invoices)})")

    # If the returned batch is smaller than per_page, we've reached the last page
    if len(invoices_batch) < per_page:
        break

    page += 1

# Step 3: Save all extracted records
os.makedirs("data", exist_ok=True)
output_path = "data/raw_invoices.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"invoices": all_invoices}, f, indent=2)

print(f"\nExtraction complete! Saved {len(all_invoices)} invoices to {output_path}")