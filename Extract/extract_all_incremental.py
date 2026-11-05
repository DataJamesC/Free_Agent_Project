# extract_all_incremental.py - Extracts only new/changed records for all 5 FreeAgent entities to S3
#
# A watermark (the latest updated_at seen) is stored per entity at s3://<bucket>/state/<entity>.json.
# Each run asks FreeAgent only for records updated since that watermark.
# If no watermark exists yet, or --full is passed, a full extract is done instead.
#
# Usage:
#   python Extract/extract_all_incremental.py                 # incremental, all entities
#   python Extract/extract_all_incremental.py --full          # ignore watermarks, extract everything
#   python Extract/extract_all_incremental.py contacts users  # only these entities

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
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
S3_BUCKET = "jc-freeagent-storage"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

ENTITIES = ["contacts", "users", "projects", "invoices", "timeslips"]

# Re-fetch a few minutes before the watermark to be safe; duplicates are removed in the Silver layer
WATERMARK_OVERLAP = timedelta(minutes=5)

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

def watermark_key(entity_name):
    # Kept outside python-import/ so COPY INTO never picks it up
    return f"state/{entity_name}.json"

def read_watermark(entity_name):
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=watermark_key(entity_name))
    except s3_client.exceptions.NoSuchKey:
        return None
    return json.loads(obj["Body"].read())["last_updated_at"]

def write_watermark(entity_name, last_updated_at):
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=watermark_key(entity_name),
        Body=json.dumps({"last_updated_at": last_updated_at}).encode("utf-8"),
        ContentType="application/json",
    )

def to_api_timestamp(watermark):
    # FreeAgent timestamps look like 2026-09-29T13:09:22.000Z
    dt = datetime.fromisoformat(watermark.replace("Z", "+00:00")) - WATERMARK_OVERLAP
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def extract_and_stream_entity(entity_name, access_token, full_refresh):
    url = f"https://api.sandbox.freeagent.com/v2/{entity_name}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "FreeAgentExtractor/1.0",
    }

    watermark = None if full_refresh else read_watermark(entity_name)
    updated_since = to_api_timestamp(watermark) if watermark else None

    all_records = []
    page = 1
    per_page = 100

    mode = f"updated since {updated_since}" if updated_since else "full extract"
    print(f"\n--- Extracting {entity_name.upper()} ({mode}) ---")

    while True:
        params = {"view": "all", "page": page, "per_page": per_page}
        if updated_since:
            params["updated_since"] = updated_since
        res = requests.get(url, params=params, headers=headers)

        # Fail rather than upload a partial extract, so the watermark isn't moved past missing records
        if res.status_code != 200:
            raise Exception(f"Error fetching {entity_name} page {page}: {res.status_code} {res.text}")

        batch = res.json().get(entity_name, [])
        if not batch:
            break

        all_records.extend(batch)
        print(f"Page {page}: Fetched {len(batch)} records (Total: {len(all_records)})")

        if len(batch) < per_page:
            break

        page += 1
        time.sleep(0.2)

    if not all_records:
        print(f"No new {entity_name} since last run, nothing uploaded")
        return

    # S3 Key: python-import/<entity>/YYYY/MM/DD/raw_<entity>_<HHMMSS>.json
    # The time in the file name stops a second run on the same day overwriting the first
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y/%m/%d")
    s3_key = f"python-import/{entity_name}/{date_prefix}/raw_{entity_name}_{now.strftime('%H%M%S')}.json"

    json_payload = json.dumps({entity_name: all_records}, indent=2).encode("utf-8")

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json_payload,
        ContentType="application/json",
    )

    print(f"Uploaded {len(all_records)} {entity_name} to s3://{S3_BUCKET}/{s3_key}")

    # Only move the watermark once the data is safely in S3.
    # Use the latest updated_at in the data, not the current time, so clock differences can't skip records.
    latest_updated_at = max(r["updated_at"] for r in all_records)
    write_watermark(entity_name, latest_updated_at)
    print(f"Watermark for {entity_name} set to {latest_updated_at}")

def main():
    parser = argparse.ArgumentParser(description="Incremental FreeAgent extract to S3")
    parser.add_argument("entities", nargs="*", default=ENTITIES,
                        help=f"Entities to extract (default: all). Options: {', '.join(ENTITIES)}")
    parser.add_argument("--full", action="store_true",
                        help="Ignore watermarks and extract everything")
    args = parser.parse_args()

    unknown = [e for e in args.entities if e not in ENTITIES]
    if unknown:
        parser.error(f"unknown entities: {', '.join(unknown)}. Options: {', '.join(ENTITIES)}")

    access_token = get_access_token()
    for entity in args.entities:
        extract_and_stream_entity(entity, access_token, args.full)

if __name__ == "__main__":
    main()
