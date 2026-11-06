# Free_Agent_Project

A data engineering training project that builds an ELT pipeline from the [FreeAgent](https://dev.freeagent.com/docs) accounting API (sandbox):

```
FreeAgent API ──► Python extract (incremental) ──► AWS S3 ──► Snowflake (bronze → silver) ──► dbt
                         ▲
                 Kestra (orchestration)
```

The course walkthroughs are in [`course_docs/`](course_docs/):

| Week | Doc | Covers |
|---|---|---|
| 1 | [Extract](course_docs/week_1_FreeAgent_extract.md) | FreeAgent sandbox, OAuth, paginated and incremental extraction in Python |
| 2 | [Load](course_docs/week_2_FreeAgent_load.md) | S3 bucket, IAM, Snowflake storage integration, stage and `COPY INTO` |
| 3 | [Transform in Snowflake](course_docs/week_3_FreeAgent_snowflake_transform.md) | Flattening JSON, stored procedures, streams, tasks, dynamic tables |
| 3 | [Transform in dbt](course_docs/week_3_FreeAgent_dbt_transform.md) | Migrating the silver layer to dbt models, tests and incremental models |
| 4 | [Orchestration](course_docs/week_4_FreeAgent_orchestration.md) | Running the extract on a schedule with Kestra |

## Repo structure

| Path | What it is |
|---|---|
| `get_token.py` | One-off OAuth step: swaps the code from your browser for a FreeAgent refresh token |
| `populate_sandbox/` | Seeds the sandbox with mock contacts, users, projects, invoices and timeslips |
| `Extract/` | Extracts each endpoint and uploads it to S3. `extract_all_incremental.py` does all five |
| `kestra/` | The Kestra flow that runs the extract |
| `requirements.txt` | Python packages for the pipeline |
| `duck_db/` | Local DuckDB version of the pipeline, used for testing only (not part of the course) |

## Setup

```
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your FreeAgent, AWS and GitHub credentials. `.env` is gitignored, never commit it.

## Running the extract

```
python Extract/extract_all_incremental.py              # all five endpoints
python Extract/extract_contacts.py                     # one endpoint
python Extract/extract_contacts.py --full              # ignore the watermark, extract everything
python Extract/extract_contacts.py --since 2026-10-01  # records updated since a date
```

Files land in S3 at `python-import/<entity>/YYYY/MM/DD/raw_<entity>_<HHMMSS>.json`.

The scripts are incremental: each run only asks FreeAgent for records updated since the last run. That point (the watermark) is stored in S3 at `python-import/_state/<entity>.json`, so it's shared between local runs and Kestra. The first run, with no watermark, is a full extract. When loading into Snowflake, always `COPY INTO` from an entity folder (e.g. `@stage/contacts/`) so the watermark files aren't loaded as data.

## Running in Kestra

1. Start Kestra (needs Docker Desktop):
   ```
   docker run --pull=always --rm -it -p 8080:8080 --user=root -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp kestra/kestra:latest server local
   ```
2. Go to localhost:8080 and create an admin user.
3. In the KV Store, in the `til.des` namespace, add every key from your `.env`: `GITHUB_USERNAME`, `GITHUB_TOKEN`, the three `FREEAGENT_*` keys and the four `AWS_*` keys.
4. Create a flow and paste in [`kestra/freeagent_pipeline.yml`](kestra/freeagent_pipeline.yml), then execute it.

This local setup doesn't keep anything when Kestra stops: the flow, KV values and admin user need re-adding each time. The flow has no trigger; see the Week 4 doc to add an hourly schedule.
