# Extract Project: FreeAgent API
### Week 1 | Thursday | Instructor Led Walkthrough

## Introduction

In this walkthrough, we build an automated extraction pipeline using Python to harvest relational accounting data from the **FreeAgent Sandbox API (v2)**. You will learn how to handle OAuth 2.0 token refreshes, navigate API rate limits, implement paginated REST extractions, and structure raw landing files for downstream data warehousing.

---

## Learning Objectives

- **Considerations for Extracting Financial Data:** OAuth token lifecycles, rate limiting, and paginated REST calls.
- **API Authentication:** Refreshing OAuth 2.0 access tokens programmatically.
- **Paginated Ingestion with Python:** Iterating through API response pages using `requests`.
- **Logging & Error Handling:** Implementing Python’s `logging` module and `try/except` blocks to handle network failure gracefully.
- **Raw Data Landing:** Saving raw JSON structures into a staged `data/` landing folder[cite: 7, 8].

---

## Considerations for Extracting Data

### Data Extraction Strategies

- **Full Extraction:** Retrieving the entire dataset from an endpoint on each run. Suitable for dimension tables like Users or Contacts that fit easily in memory[cite: 8].
- **Incremental Extraction:** Fetching only records created or modified since the last extraction execution[cite: 8]. Essential for high-volume event data or historical financial records[cite: 8].
- **API Rate Limiting:** FreeAgent enforces a rate limit of **120 requests per minute** (~2 requests per second). Extraction loops must incorporate sleep throttles (`time.sleep(0.5)`) to avoid `429 Too Many Requests` status codes.

### Key Extraction Challenges

- **Token Expiration:** FreeAgent access tokens expire after 1 hour. Extraction pipelines must automatically negotiate new access tokens using a persistent `REFRESH_TOKEN`.
- **Relational URI Foreign Keys:** FreeAgent represents primary and foreign keys as full resource URLs (e.g., `"contact": "https://api.sandbox.freeagent.com/v2/contacts/12345"`). Extraction scripts must capture these raw strings so transformation layers can resolve them into relational keys.
- **Data Diversity & Schema Evolution:** Nested arrays (such as `invoice_items` inside an invoice) require careful extraction without dropping sub-fields[cite: 7, 8].

---

## FreeAgent REST API v2 Overview

FreeAgent uses standard HTTP verbs and JSON payloads across its REST endpoints:

| Endpoint | Entity Description | Key Modeling Purpose |
| :--- | :--- | :--- |
| `/v2/contacts` | Clients and Suppliers | **Customer / Supplier Dimension** |
| `/v2/users` | Internal Staff and Directors | **Employee Dimension** |
| `/v2/projects` | Billable Engagements | **Project Dimension** (links work to customers) |
| `/v2/invoices` | Billing Summaries & Line Items | **Sales Revenue Fact Table** |
| `/v2/timeslips` | Logged Work Hours | **Labor & Utilization Fact Table** |

---

## Environment Setup

1. **Directory Structure:**
   ```powershell
   mkdir Free_Agent_Project
   cd Free_Agent_Project
   python -m venv .venv
   .venv\Scripts\activate