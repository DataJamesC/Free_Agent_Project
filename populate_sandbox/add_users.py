# seed_users.py - Generates mock Users/Employees in FreeAgent Sandbox
# Docs: https://dev.freeagent.com/docs/users

import os
import random
import time
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
        "User-Agent": "FreeAgentUserSeeder/1.0",
    }
)

first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Jamie", "Avery"]
last_names = ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson", "Davies", "Patel", "Wright"]
roles = ["Director", "Employee", "Employee", "Employee", "Shareholder"]

print("\n--- Seeding Users ---")

for i in range(1, 51):
    f_name = random.choice(first_names)
    l_name = f"{random.choice(last_names)}{i}"
    
    user_payload = {
        "user": {
            "first_name": f_name,
            "last_name": l_name,
            "email": f"{f_name.lower()}.{l_name.lower()}@example.com",
            "role": random.choice(roles),
            "permission_level": random.choice([1, 4, 7, 8]),  # 1: Time, 4: Invoices, 8: Full
            "opening_mileage": "0.0",
        }
    }

    res = session.post("https://api.sandbox.freeagent.com/v2/users", json=user_payload)

    if res.status_code in (200, 201):
        user_url = res.json()["user"]["url"]
        print(f"[{i}/50] Created User: {f_name} {l_name} ({user_url})")
    else:
        print(f"[{i}/50] Failed User: {res.status_code} - {res.text}")

    time.sleep(0.5)

print("\n--- User Seeding Complete! ---")