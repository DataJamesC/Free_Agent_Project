# add_contacts.py - Seeds mock contacts into FreeAgent Sandbox API
import os
import random
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("FREEAGENT_REFRESH_TOKEN")

# Step 1: Refresh OAuth Token
token_url = "https://api.sandbox.freeagent.com/v2/token_endpoint"
token_response = requests.post(
    token_url,
    data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={"Accept": "application/json"},
)

if token_response.status_code != 200:
    print(f"Auth Error ({token_response.status_code}): {token_response.text}")
    exit(1)

access_token = token_response.json()["access_token"]

# Step 2: Mock Contact Data Pools
FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Ian", "Julia"
]
LAST_NAMES = [
    "Smith", "Jones", "Taylor", "Brown", "Williams",
    "Wilson", "Johnson", "Davies", "Patel", "Wright"
]
COMPANIES = [
    "Apex Digital", "Blue Horizon Media", "CloudPeak Consulting",
    "Delta Logistics", "Echo Ventures", "Frontier Labs",
    "Greenfield Analytics", "Hyperion Tech", "Ironclad Security", "Jupiter Media"
]
DOMAINS = ["example.com", "testcompany.co.uk", "demoagency.com", "cloudcorp.io"]

# Step 3: Populate Mock Contacts via API POST Requests
contacts_url = "https://api.sandbox.freeagent.com/v2/contacts"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "FreeAgentSeeder/1.0",
}

NUM_CONTACTS_TO_CREATE = 25
print(f"Starting creation of {NUM_CONTACTS_TO_CREATE} sample contacts in FreeAgent Sandbox...\n")

for i in range(NUM_CONTACTS_TO_CREATE):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    org = f"{random.choice(COMPANIES)} {random.randint(10, 99)}"
    email = f"{first.lower()}.{last.lower()}_{random.randint(100, 999)}@{random.choice(DOMAINS)}"

    payload = {
        "contact": {
            "first_name": first,
            "last_name": last,
            "organisation_name": org,
            "email": email,
            "status": "Active"
        }
    }

    res = requests.post(contacts_url, json=payload, headers=headers)

    if res.status_code == 201:
        contact_data = res.json().get("contact", {})
        contact_url = contact_data.get("url")
        print(f"[{i+1}/{NUM_CONTACTS_TO_CREATE}] Created: {first} {last} ({org}) -> {contact_url}")
    else:
        print(f"[{i+1}/{NUM_CONTACTS_TO_CREATE}] Error ({res.status_code}): {res.text}")

    # Throttle slightly to respect API rate limits
    time.sleep(0.2)

print("\nFinished seeding contacts! You can now run the extraction script to pull them.")