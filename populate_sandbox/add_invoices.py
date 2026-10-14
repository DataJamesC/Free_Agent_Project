# add_invoices.py - Creates Contacts and Invoices in FreeAgent Sandbox

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

company_types = ["Corp", "Inc", "Ltd", "Holdings", "Tech", "Solutions"]
item_types = ["Hours", "Days", "Products", "Services"]
descriptions = [
    "Data Engineering Consulting",
    "Pipeline Optimization",
    "Cloud Architecture Migration",
    "API Integration Development",
]

# Step 2: Create Contacts
contact_urls = []
print("\n--- Phase 1: Creating Contacts ---")

for i in range(1, 101):
    company_name = f"Client {i} {random.choice(company_types)}"
    contact_payload = {
        "contact": {
            "first_name": "Contact",
            "last_name": str(i),
            "organisation_name": company_name,
            "email": f"billing@client{i}.example.com",
        }
    }

    res = session.post(
        "https://api.sandbox.freeagent.com/v2/contacts", json=contact_payload
    )

    if res.status_code in (200, 201):
        url = res.json()["contact"]["url"]
        contact_urls.append(url)
        print(f"[{i}/100] Created Contact: {company_name}")
    else:
        print(f"[{i}/100] Failed Contact: {res.status_code}")

    time.sleep(0.5)

if not contact_urls:
    print("No contacts were created. Aborting invoice creation.")
    exit(1)

# Step 3: Create Invoices
print("\n--- Phase 2: Creating Invoices ---")
today_str = datetime.now().strftime("%Y-%m-%d")

for i in range(1, 1001):
    target_contact = random.choice(contact_urls)

    invoice_payload = {
        "invoice": {
            "contact": target_contact,
            "dated_on": today_str,
            "payment_terms_in_days": random.choice([7, 14, 30, 60]),
            "currency": "GBP",
            "invoice_items": [
                {
                    "description": random.choice(descriptions),
                    "price": f"{random.randint(250, 5000):.2f}",
                    "quantity": f"{random.randint(1, 20):.1f}",
                    "item_type": random.choice(item_types),
                    "sales_tax_rate": "0.0",
                }
            ],
        }
    }

    res = session.post(
        "https://api.sandbox.freeagent.com/v2/invoices", json=invoice_payload
    )

    if res.status_code in (200, 201):
        print(f"[{i}/1000] Created Invoice")
    else:
        print(f"[{i}/1000] Failed Invoice: {res.status_code} - {res.text}")

    time.sleep(0.5)

print("\n--- Seeding Complete! ---")