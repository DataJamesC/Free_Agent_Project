# extract_all_entities.py - Extracts all 5 FreeAgent entities to entity-partitioned S3 paths

import json
import os
import time
from datetime import datetime, timezone
import boto3
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("FREEAGENT_REFRESH_TOKEN")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "jc-freeagent-storage")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

ENTITIES = ["contacts", "users", "projects", "invoices", "timeslips"]

def get_access_token():
    token_url = "https://api.sandbox.freeagent.com/v2/token_endpoint"
    res = requests.post(
        token_url,
        data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={"Accept": "application/json"},
    )
    if res.status_code != 200:
        raise Exception(f"Auth Failed: {res.status_code} - {res.text}")
    return res.json()["access_token"]

def extract_and_stream_entity(entity_name, access_token):
    url = f"https://api.sandbox.freeagent.com/v2/{entity_name}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "FreeAgentExtractor/1.0",
    }

    all_records = []
    page = 1
    per_page = 100

    print(f"\n--- Extracting {entity_name.upper()} ---")

    while True:
        params = {"view": "all", "page": page, "per_page": per_page}
        res = requests.get(url, params=params, headers=headers)

        if res.status_code != 200:
            print(f"Error fetching {entity_name} page {page}: {res.status_code} {res.text}")
            break

        batch = res.json().get(entity_name, [])
        if not batch:
            break

        all_records.extend(batch)
        print(f"Page {page}: Fetched {len(batch)} records (Total: {len(all_records)})")

        if len(batch) < per_page:
            break

        page += 1
        time.sleep(0.2)

    # S3 Key: python-import/<entity>/YYYY/MM/DD/raw_<entity>.json
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y/%m/%d")
    s3_key = f"python-import/{entity_name}/{date_prefix}/raw_{entity_name}.json"

    json_payload = json.dumps({entity_name: all_records}, indent=2).encode("utf-8")

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json_payload,
        ContentType="application/json",
    )

    print(f"Uploaded {len(all_records)} {entity_name} to s3://{S3_BUCKET}/{s3_key}")

def main():
    access_token = get_access_token()
    for entity in ENTITIES:
        extract_and_stream_entity(entity, access_token)

if __name__ == "__main__":
    main()