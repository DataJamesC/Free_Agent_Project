# Extract ALL Projects (Project Dimension) with Pagination from FreeAgent API v2
# Docs: https://dev.freeagent.com/docs/projects

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
url = "https://api.sandbox.freeagent.com/v2/projects"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

all_projects = []
page = 1
per_page = 100

print("Starting paginated projects extraction...")

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
    projects_batch = data.get("projects", [])

    if not projects_batch:
        break

    all_projects.extend(projects_batch)
    print(f"Page {page}: Fetched {len(projects_batch)} projects (Total: {len(all_projects)})")

    if len(projects_batch) < per_page:
        break

    page += 1

# Step 3: Save all extracted records
os.makedirs("data", exist_ok=True)
output_path = "data/raw_projects.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"projects": all_projects}, f, indent=2)

print(f"\nExtraction complete! Saved {len(all_projects)} projects to {output_path}")