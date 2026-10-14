# seed_timeslips.py - Generates mock Timeslips (Labor Fact) in FreeAgent Sandbox
# Docs: https://dev.freeagent.com/docs/timeslips

import os
import random
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

# Generation count: Start with 10 to test, then change to 100+ for bulk
COUNT = 250

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
        "User-Agent": "FreeAgentTimeslipSeeder/1.0",
    }
)

# Step 2: Fetch existing Users and Projects
print("Fetching existing Users and Projects...")
users_res = session.get("https://api.sandbox.freeagent.com/v2/users?per_page=100")
projects_res = session.get("https://api.sandbox.freeagent.com/v2/projects?per_page=100")

users = users_res.json().get("users", [])
projects = projects_res.json().get("projects", [])

if not users or not projects:
    print("Error: Missing users or projects in Sandbox. Make sure users and projects exist first!")
    exit(1)

user_urls = [u["url"] for u in users]
project_urls = [p["url"] for p in projects]

# Step 3: Fetch or Create a Task
tasks_res = session.get("https://api.sandbox.freeagent.com/v2/tasks?per_page=100")
tasks = tasks_res.json().get("tasks", [])

if not tasks:
    print("No existing tasks found. Creating a default task...")
    task_payload = {
        "task": {
            "name": "General Consulting",
            "billing_rate": "100.0",
            "billing_period": "hour",
        }
    }
    create_task_res = session.post(
        f"https://api.sandbox.freeagent.com/v2/tasks?project={project_urls[0]}",
        json=task_payload,
    )
    if create_task_res.status_code in (200, 201):
        tasks = [create_task_res.json()["task"]]
    else:
        print(f"Failed to create task: {create_task_res.text}")
        exit(1)

task_urls = [t["url"] for t in tasks]

comments = [
    "Configured ETL pipeline logic",
    "Data modeling and star schema design",
    "Optimized SQL queries in DuckDB",
    "Built automated API extraction scripts",
    "Data validation and quality checks",
    "Client requirement gathering and sprint review",
]

print(f"\n--- Seeding {COUNT} Timeslips ---")

for i in range(1, COUNT + 1):
    random_days_ago = random.randint(1, 30)
    dated_on = (datetime.now() - timedelta(days=random_days_ago)).strftime("%Y-%m-%d")

    timeslip_payload = {
        "timeslip": {
            "user": random.choice(user_urls),
            "project": random.choice(project_urls),
            "task": random.choice(task_urls),
            "dated_on": dated_on,
            "hours": str(random.choice([1.0, 2.0, 3.5, 4.0, 7.5, 8.0])),
            "comment": random.choice(comments),
        }
    }

    res = session.post("https://api.sandbox.freeagent.com/v2/timeslips", json=timeslip_payload)

    if res.status_code in (200, 201):
        print(f"[{i}/{COUNT}] Created Timeslip for {dated_on}")
    else:
        print(f"[{i}/{COUNT}] Failed Timeslip ({res.status_code}): {res.text}")

    time.sleep(0.5)

print(f"\n--- Timeslip Seeding Complete ({COUNT} records)! ---")