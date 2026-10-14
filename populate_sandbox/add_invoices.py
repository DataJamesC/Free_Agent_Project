# add_invoices.py - Seeds Invoices using Existing Contacts in FreeAgent Sandbox

import os
import random
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("FREEAGENT_REFRESH_TOKEN")

# Step 1: Refresh Access Token
print("Refreshing access token...")
token_res = requests.post(
    "https://api.sandbox.freeagent.com/v2/token_endpoint",
    data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={"Accept": "application/json"},
)

if token_res.status_code != 200:
    print(f"Auth Error: {token_res.text}")
    exit(1)

access_token = token_res.json()["access_token"]

session = requests.Session()
session.headers.update(
    {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "FreeAgentBulkSeeder/1.0",
    }
)

# Step 2: Fetch Existing Contacts from FreeAgent
print("\n--- Phase 1: Fetching Existing Contacts ---")
contact_urls = []
page = 1
per_page = 100

while True:
    params = {"view": "all", "page": page, "per_page": per_page}
    res = session.get("https://api.sandbox.freeagent.com/v2/contacts", params=params)

    if res.status_code != 200:
        print(f"Error fetching contacts (Page {page}): {res.status_code} - {res.text}")
        break

    contacts_batch = res.json().get("contacts", [])
    if not contacts_batch:
        break

    for contact in contacts_batch:
        if "url" in contact:
            contact_urls.append(contact["url"])

    if len(contacts_batch) < per_page:
        break

    page += 1

print(f"Successfully loaded {len(contact_urls)} existing contacts from Sandbox.")

if not contact_urls:
    print("No contacts found in Sandbox! Please run 'add_contacts.py' first.")
    exit(1)

# Step 3: Seed Invoices Linked to Existing Contacts
NUM_INVOICES_TO_CREATE = 30 
print(f"\n--- Phase 2: Creating {NUM_INVOICES_TO_CREATE} Invoices ---")

item_types = ["Hours", "Days", "Products", "Services"]
descriptions = [
    "Data Engineering Consulting",
    "Pipeline Optimization",
    "Cloud Architecture Migration",
    "API Integration Development",
    "Snowflake Star Schema Modeling",
    "Data Pipeline Auditing",
]

today = datetime.now()

for i in range(1, NUM_INVOICES_TO_CREATE + 1):
    target_contact = random.choice(contact_urls)

    # Vary invoice dates across the last 90 days for realistic aging analysis
    random_days_ago = random.randint(0, 90)
    invoice_date = (today - timedelta(days=random_days_ago)).strftime("%Y-%m-%d")

    invoice_payload = {
        "invoice": {
            "contact": target_contact,
            "dated_on": invoice_date,
            "payment_terms_in_days": random.choice([7, 14, 30, 60]),
            "currency": "GBP",
            "invoice_items": [
                {
                    "description": random.choice(descriptions),
                    "price": f"{random.randint(300, 4500):.2f}",
                    "quantity": f"{random.randint(1, 15):.1f}",
                    "item_type": random.choice(item_types),
                    "sales_tax_rate": "20.0",  # Standard 20% VAT
                }
            ],
        }
    }

    res = session.post(
        "https://api.sandbox.freeagent.com/v2/invoices", json=invoice_payload
    )

    if res.status_code in (200, 201):
        invoice_url = res.json().get("invoice", {}).get("url")
        print(f"[{i}/{NUM_INVOICES_TO_CREATE}] Created Invoice: {invoice_url}")
    else:
        print(f"[{i}/{NUM_INVOICES_TO_CREATE}] Failed Invoice: {res.status_code} - {res.text}")

    # Small delay to keep within API rate limits
    time.sleep(0.2)

print("\n--- Invoice Seeding Complete! ---")