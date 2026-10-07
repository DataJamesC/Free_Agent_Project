# Extract ALL Invoices with Pagination from FreeAgent API v2 and stream directly to S3
import json
import os
from datetime import datetime, timezone
import boto3
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# FreeAgent Credentials
CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("FREEAGENT_REFRESH_TOKEN")

# AWS Credentials & Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

S3_BUCKET = "jc-freeagent-storage"

# Initialize S3 Client explicitly using environment variables
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

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

    if not invoices_batch:
        break

    all_invoices.extend(invoices_batch)
    print(f"Page {page}: Fetched {len(invoices_batch)} invoices (Total: {len(all_invoices)})")

    if len(invoices_batch) < per_page:
        break

    page += 1

# Step 3: Generate Dynamic Date-Partitioned Key (YYYY/MM/DD)
now = datetime.now(timezone.utc)
date_prefix = now.strftime("%Y/%m/%d")
s3_key = f"python-import/{date_prefix}/raw_invoices.json"

# Step 4: Stream Payload Directly to AWS S3 (In-Memory)
json_payload = json.dumps({"invoices": all_invoices}, indent=2).encode("utf-8")

s3_client.put_object(
    Bucket=S3_BUCKET,
    Key=s3_key,
    Body=json_payload,
    ContentType="application/json",
)

print(f"\nExtraction complete! Uploaded {len(all_invoices)} invoices to s3://{S3_BUCKET}/{s3_key}")