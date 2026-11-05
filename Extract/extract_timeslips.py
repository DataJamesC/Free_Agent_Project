# Extract ALL Timeslips (Labor Fact Table) with Pagination from FreeAgent API v2 and stream directly to S3
#
# Only records updated since the last run are extracted. The latest updated_at seen is stored
# as a watermark at s3://<bucket>/python-import/_state/timeslips.json and passed to the API as updated_since.
#
# Usage:
#   python Extract/extract_timeslips.py                     # incremental (full extract on first run)
#   python Extract/extract_timeslips.py --full              # ignore the watermark, extract everything
#   python Extract/extract_timeslips.py --since 2026-10-01  # extract records updated since a date
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
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
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")

S3_BUCKET = os.getenv("AWS_BUCKET_NAME")

if not S3_BUCKET:
    print("Error: AWS_BUCKET_NAME missing from .env")
    exit(1)

# Watermark location. It sits inside python-import/ because that's the only prefix the Week 2
# IAM policy allows, but outside python-import/timeslips/ so COPY INTO never picks it up
WATERMARK_KEY = "python-import/_state/timeslips.json"

# Re-fetch a few seconds before the watermark to be safe; duplicates are removed in the Silver layer
WATERMARK_OVERLAP = timedelta(seconds=5)

parser = argparse.ArgumentParser(description="Extract FreeAgent timeslips to S3")
parser.add_argument("--full", action="store_true", help="Ignore the watermark and extract everything")
parser.add_argument("--since", help="Extract records updated since this date/time, e.g. 2026-10-01")
args = parser.parse_args()

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

# Step 2: Work out the date filter (updated_since)
updated_since = None

if args.since:
    updated_since = datetime.fromisoformat(args.since).strftime("%Y-%m-%dT%H:%M:%S.000Z")
elif not args.full:
    # Check the watermark exists with a list request first. The IAM policy only allows listing
    # within python-import/, so a get_object on a missing file returns AccessDenied, not NoSuchKey
    listing = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=WATERMARK_KEY)
    if listing.get("KeyCount", 0) > 0:
        watermark_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=WATERMARK_KEY)
        watermark = json.loads(watermark_obj["Body"].read())["last_updated_at"]
        # FreeAgent timestamps look like 2026-09-29T13:09:22.000Z
        watermark_dt = datetime.fromisoformat(watermark.replace("Z", "+00:00")) - WATERMARK_OVERLAP
        updated_since = watermark_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        print("No watermark found, running a full extract")

# Step 3: Setup Paginated Extraction Loop
url = "https://api.sandbox.freeagent.com/v2/timeslips"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

all_timeslips = []
page = 1
per_page = 100

if updated_since:
    print(f"Starting paginated timeslips extraction (updated since {updated_since})...")
else:
    print("Starting paginated timeslips extraction (full extract)...")

while True:
    params = {
        "view": "all",
        "page": page,
        "per_page": per_page,
    }
    if updated_since:
        params["updated_since"] = updated_since

    response = requests.get(url, params=params, headers=headers)

    # Stop rather than upload a partial extract, so the watermark isn't moved past missing records
    if response.status_code != 200:
        print(f"Error on page {page} ({response.status_code}): {response.text}")
        exit(1)

    data = response.json()
    timeslips_batch = data.get("timeslips", [])

    if not timeslips_batch:
        break

    all_timeslips.extend(timeslips_batch)
    print(f"Page {page}: Fetched {len(timeslips_batch)} timeslips (Total: {len(all_timeslips)})")

    if len(timeslips_batch) < per_page:
        break

    page += 1

if not all_timeslips:
    print("\nNo new timeslips since the last run, nothing uploaded.")
    exit(0)

# Step 4: Generate Dynamic Date-Partitioned Key (timeslips/YYYY/MM/DD/raw_timeslips_HHMMSS.json)
# The time in the file name stops a second run on the same day overwriting the first
now = datetime.now(timezone.utc)
date_prefix = now.strftime("%Y/%m/%d")
s3_key = f"python-import/timeslips/{date_prefix}/raw_timeslips_{now.strftime('%H%M%S')}.json"

# Step 5: Stream Payload Directly to AWS S3 (In-Memory)
json_payload = json.dumps({"timeslips": all_timeslips}, indent=2).encode("utf-8")

s3_client.put_object(
    Bucket=S3_BUCKET,
    Key=s3_key,
    Body=json_payload,
    ContentType="application/json",
)

print(f"\nExtraction complete! Uploaded {len(all_timeslips)} timeslips to s3://{S3_BUCKET}/{s3_key}")

# Step 6: Move the watermark, only once the data is safely in S3.
# Use the latest updated_at in the data, not the current time, so clock differences can't skip records.
latest_updated_at = max(record["updated_at"] for record in all_timeslips)
s3_client.put_object(
    Bucket=S3_BUCKET,
    Key=WATERMARK_KEY,
    Body=json.dumps({"last_updated_at": latest_updated_at}).encode("utf-8"),
    ContentType="application/json",
)

print(f"Watermark set to {latest_updated_at}")
