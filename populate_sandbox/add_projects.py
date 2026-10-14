# seed_projects.py - Generates mock Projects in FreeAgent Sandbox
# Docs: https://dev.freeagent.com/docs/projects

import os
import random
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Set generation count
COUNT = 200

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
        "User-Agent": "FreeAgentProjectSeeder/1.0",
    }
)

# Step 2: Fetch existing Contacts to link projects against
print("Fetching contacts list...")
contacts_res = session.get("https://api.sandbox.freeagent.com/v2/contacts?per_page=100")

if contacts_res.status_code != 200:
    print(f"Failed to fetch contacts: {contacts_res.text}")
    exit(1)

contacts = contacts_res.json().get("contacts", [])
if not contacts:
    print("No contacts found in Sandbox. Please run add_invoices.py or seed_bulk_sandbox.py first!")
    exit(1)

contact_urls = [c["url"] for c in contacts]
print(f"Found {len(contact_urls)} contacts to assign projects to.")

# Random name building blocks
prefixes = ["Cloud", "Data", "Security", "AI", "Mobile", "ERP", "Analytics", "CRM", "Infrastructure"]
actions = ["Migration", "Replatforming", "Audit", "Implementation", "Optimization", "Integration", "Redesign"]
statuses = ["Active", "Completed", "Cancelled", "Active", "Active"]  # Weight toward Active
budget_units_list = ["Hours", "Days", "Monetary"]

print(f"\n--- Seeding {COUNT} Projects ---")

for i in range(1, COUNT + 1):
    target_contact = random.choice(contact_urls)
    project_name = f"{random.choice(prefixes)} {random.choice(actions)} - Phase {random.randint(1, 8)}"
    budget_unit = random.choice(budget_units_list)

    project_payload = {
        "project": {
            "contact": target_contact,
            "name": project_name,
            "status": random.choice(statuses),
            "currency": "GBP",
            "budget_units": budget_unit,
            "budget": str(float(random.randint(20, 500))),
            "normal_billing_rate": f"{random.randint(50, 150):.2f}",
            "billing_period": "hour" if budget_unit == "Hours" else "day",
            "contract_po_reference": f"PO-{random.randint(1000, 9999)}",
        }
    }

    res = session.post("https://api.sandbox.freeagent.com/v2/projects", json=project_payload)

    if res.status_code in (200, 201):
        p_url = res.json()["project"]["url"]
        print(f"[{i}/{COUNT}] Created Project: {project_name}")
    else:
        print(f"[{i}/{COUNT}] Failed Project ({res.status_code}): {res.text}")

    # Sleep to respect rate limits
    time.sleep(0.5)

print(f"\n--- Project Seeding Complete ({COUNT} records)! ---")