# Extract Project: FreeAgent API
### Week 1 | Thursday | Instructor Led Walkthrough

## Introduction

## Learning Objectives
- Considerations for Extracting Data
- Introduction to Airbyte Cloud
- Extracting with Python

## Considerations for Extracting Data

### Key Terminologies for Extract & Load
- **Full Extraction** Retrieving the entire dataset from the source, regardless of whether the data has changed. It’s used when data needs to be completely refreshed.
- **Incremental Stream Extraction** Only the new or changed data since the last extraction. It’s efficient for large datasets where full extraction is not necessary. Techniques like Change Data Capture (CDC) are used for this.
- **Incremental Batch Extraction** The data extraction process runs on a predefined schedule determined by data teams, e.g. outside business hours. Batch processing is used when the dataset is too large to be extracted at once or when constant updates are unnecessary.

### Typical Data Extraction Methods
- **Database Querying and Exports** For relational databases, SQL is used to query and extract data. You can retrieve specific data, entire tables, or join multiple tables to get the information. Many database management systems (DBMS) also provide export functions to save query results as files in various formats (e.g., CSV, Excel) for further analysis.‍
- **API Calls and Integrations** When dealing with web-based services and applications, you can use API calls to request data in a structured format (usually JSON or XML). APIs provide a standardized way to access and extract data from these sources. You can also automate data extraction using integration platforms like Airbyte, Zapier, Integromat, or custom-built solutions.
- **File Parsing** Data can be extracted from various file formats, such as CSV, Excel, JSON, XML, or flat files. Programming languages have libraries and tools for reading and parsing these files. For structured data files like CSV or Excel, you can use libraries like pandas (Python) to read and manipulate the data.

Data extraction methods can also include: Web Scraping and Parsing, Optical Character Recognition (OCR), Email Extraction, Log File Parsing, Data Extraction from PDFs, Data Capture from Sensors and IoT Devices.

### Challenges with Data Extraction 
- **Data Diversity** Managing various data formats and structures.
- **Quality Assurance** Ensuring data accuracy, completeness, and consistency.
- **Scalability** Handling large volumes of data efficiently.
- **Security Concerns** Protecting sensitive information during extraction.
- **Legacy System Integration** Bridging the gap between old and new technologies.
- **Budget Constraints** Balancing costs with the need for effective extraction solutions.
- **Compliance** Adhering to data governance standards and regulations.

## Python Environment Setup

Create a directory for 'FreeAgent'
```
mkdir -p FreeAgent
```

Navigate to the new folder.
```
cd FreeAgent
```

Create a virtual environment.
```
python -m venv .venv
```

Create a .env file.
```
touch .env
```

Edit the .env file to include the following variables. We will edit these with the correct keys once they've been created.
```
FREEAGENT_CLIENT_ID = 'xxxxxxxxxxxxxxxxxx'
FREEAGENT_CLIENT_SECRET = 'xxxxxxxxxxxxxxxxxx'
FREEAGENT_REFRESH_TOKEN = 'xxxxxxxxxxxxxxxxxx'
```

Activate the environment
```
# Windows
.venv/Scripts/activate

# Mac / Linux
source .venv/bin/activate
```

Install required packages
```
pip install python-dotenv requests
```

Create a requirements.txt file
```
pip freeze > requirements.txt
```

Create/edit a .gitignore file to prevent your credentials and data from being shared.
```
*.env
.venv
*\data*
```

## The Free Agent Sandbox

### Introduction

We need to start by making a sandbox FreeAgent account for our new businesses. We'll then be able to populate these sandboxes with fake data, simulating a production FreeAgent and allowing us to create a pipeline for simulated business data. 

### Sign up for your sandbox

On the sandbox freeagent website (https://signup.sandbox.freeagent.com/signup), sign up for a free trial account, valid for 30 days.

The details that you put into your business can be anything and do not factor into how we proceed.

### Register an Application on the FreeAgent Developer Dashboard

Navigate to the FreeAgent Developer Dashboard (https://dev.freeagent.com/) and log in using the Sandbox account email and password that we just created.

Click Create New App. Give the app a name and description of your choosing. Add http://localhost:8080/callback to the section with OAuth redirect URIs (no need to remove the other two, though they aren't needed now). Click Create App, and note the OAuth identifier and OAuth Secret. These will be added to our .env file later to act as the credentials for our API calls.

### Obtain your Initial Authorization Code

FreeAgent requires an OAuth 2.0 handshake before you can call the API via code. We need to find our Initial Authorization Code, which we can then use to generate a Refresh token. This Refresh token can then live in our .env file, so this is a one-time process.

Copy the following URL, replacing <YOUR_CLIENT_ID> with your actual OAuth Identifier logged above:
```
https://api.sandbox.freeagent.com/v2/approve_app?client_id=<YOUR_CLIENT_ID>&response_type=code&redirect_uri=http://localhost:8080/callback
```

This should pop up a window Approving account access for the app you just created. Hit approve. (you may need to confirm your FreeAgent account first if not done earlier).

The next page should read 'This site can't be reached'. Have no fear, this has still worked. The url should look something like this - http://localhost:8080/callback?code=1JyWiv3R8txB_IEMjV8_FxkGfvstA2QgKPJpUV1vz&state=. Make a note of the code. This is your Initial Authorization Code.

### Using this code to get your FreeAgent Refresh Token

Create a .py file in your repo called get_token.py. Use the below script to generate your Refresh Token, and store it in your .env 

<details>
<summary>get_token script</summary>

```
import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: FREEAGENT_CLIENT_ID or FREEAGENT_CLIENT_SECRET missing from .env")
    exit(1)

# Prompt interactively so no code is ever saved to disk
auth_code = input("Paste the 'code' parameter from your browser URL: ").strip()

url = "https://api.sandbox.freeagent.com/v2/token_endpoint"

payload = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": "http://localhost:8080/callback",
}

response = requests.post(
    url,
    data=payload,
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={"Accept": "application/json"},
)

if response.status_code == 200:
    data = response.json()
    print("\n Success! Add this line to your .env file:\n")
    print(f'FREEAGENT_REFRESH_TOKEN="{data.get("refresh_token")}"')
else:
    print(f"\n Error {response.status_code}: {response.text}")
```
</details>

## Populating the Sand Box

We need to populate our sand box account with fake data. You can use the scripts provided in the 'populate sandbox' folder to get a headstart. If we run these in our pipeline before we run our extract scripts later, it can simulate new data being created in our account.

## Extracting with Python

### Freeagent's API

- Documentation: https://dev.freeagent.com/docs

FreeAgent uses standard HTTP verbs and JSON payloads across its REST endpoints:

| Endpoint | Entity Description | Key Modeling Purpose |
| :--- | :--- | :--- |
| `/v2/contacts` | Clients and Suppliers | **Customer / Supplier Dimension** |
| `/v2/users` | Internal Staff and Directors | **Employee Dimension** |
| `/v2/projects` | Billable Engagements | **Project Dimension** (links work to customers) |
| `/v2/invoices` | Billing Summaries & Line Items | **Sales Revenue Fact Table** |
| `/v2/timeslips` | Logged Work Hours | **Labor & Utilization Fact Table** |

### Make a plan

Plan how you would write your Python scripts to extract the data from this API. This does not need to be perfect code, in fact it should be "pseudo" code - a plain english description of the steps you'd like to take. 

For example:

- Create Python file
- Check Python version
- Decide what libraries to use
- etc.

Consider the concepts discussed in Extract Fundamentals and think about how you would incorporate them.

### The Calls
Scripts need to start by refreshing the Access Token using the endpoint: https://api.sandbox.freeagent.com/v2/token_endpoint. You can see an example of this in the population scripts we just used. 

### Example url, headers
url = "https://api.sandbox.freeagent.com/v2/invoices"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

# Make the Get
response = requests.get(url, params=params, headers=headers)


### Python Script

Now it's time to write your Python script. Build up the script incrementally, first verifying that you're able to connect to the API. Then work to include elements of your plan.

Below is an example Python script that extracts data from the contacts endpoint. Only use this if you're struggling.


<details>
<summary>freeagent_extract</summary>

```
# Extract ALL Contacts (Customer/Supplier Dimension) with Pagination from FreeAgent API v2
# Docs: https://dev.freeagent.com/docs/contacts

import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("FREEAGENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEAGENT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("FREEAGENT_REFRESH_TOKEN")

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
url = "https://api.sandbox.freeagent.com/v2/contacts"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": "FreeAgentExtractor/1.0",
}

all_contacts = []
page = 1
per_page = 100

print("Starting paginated contacts extraction...")

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
    contacts_batch = data.get("contacts", [])

    # Exit loop if no records are returned
    if not contacts_batch:
        break

    all_contacts.extend(contacts_batch)
    print(f"Page {page}: Fetched {len(contacts_batch)} contacts (Total: {len(all_contacts)})")

    # If the returned batch is smaller than per_page, we've reached the last page
    if len(contacts_batch) < per_page:
        break

    page += 1

# Step 3: Save all extracted records
os.makedirs("data", exist_ok=True)
output_path = "data/raw_contacts.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"contacts": all_contacts}, f, indent=2)

print(f"\nExtraction complete! Saved {len(all_contacts)} contacts to {output_path}")

```

</details>

#### Logging

Logging helps us retain an audit of how our scripts run to:
- Debug failures (API failures, rate limits, etc.)
- Monitor performance of pipeline
- Audit trail of what happened when

`logging` is a part of Python's standard library. (no need for pip install)
[https://docs.python.org/3/library/logging.html](https://docs.python.org/3/library/logging.html)

##### When to use logging

You can access logging functionality by creating a logger via `logger = getLogger()`, and then calling the logger’s `debug()`, `info()`, `warning()`, `error()` and `critical()` methods. To determine when to use logging, and to see which logger methods to use when, see the table below. It states, for each of a set of common tasks, the best tool to use for that task.

| Task you want to perform | The best tool for the task |
|---------------------------|----------------------------|
| Display console output for ordinary usage of a command line script or program | `print()` |
| Report events that occur during normal operation of a program (e.g. for status monitoring or fault investigation) | A logger's `info()` (or `debug()` method for very detailed output for diagnostic purposes) |
| Issue a warning regarding a particular runtime event | `warnings.warn()` in library code if the issue is avoidable and the client application should be modified to eliminate the warning<br><br>A logger's `warning()` method if there is nothing the client application can do about the situation, but the event should still be noted |
| Report an error regarding a particular runtime event | Raise an exception |
| Report suppression of an error without raising an exception (e.g. error handler in a long-running server process) | A logger's `error()`, `exception()` or `critical()` method as appropriate for the specific error and application domain |

The logger methods are named after the level or severity of the events they are used to track. The standard levels and their applicability are described below (in increasing order of severity):

| Level | When it's used |
|-------|----------------|
| `DEBUG` | Detailed information, typically of interest only when diagnosing problems. |
| `INFO` | Confirmation that things are working as expected. |
| `WARNING` | An indication that something unexpected happened, or indicative of some problem in the near future (e.g. 'disk space low'). The software is still working as expected. |
| `ERROR` | Due to a more serious problem, the software has not been able to perform some function. |
| `CRITICAL` | A serious error, indicating that the program itself may be unable to continue running. |

##### Basic Config for logs

Default settings and key arguments 
```
logging.basicConfig(
    filename = "filename",
    filemode = "a", # Append new logs to file by default, can be "w" to overwrite the file
    format = "levelname:name:message", # format for content output in log file
    level=logging.WARNING, # minimum serverity for log to be recorded in a log file
)
```

##### Assign Logger
logger = logging.getLogger()

##### Set Logging Messages
Recall the Log Level serverity hierarchy: DEBUG < INFO < WARNING < ERROR < CRITICAL

Applied through these methods
- logger.debug("")
- logger.info("")  
- logger.warning("")       
- logger.error("") 
- logger.critical("") 

Setting `level=logging.INFO` will only capture message of status INFO and higher

##### Simple Logging Example

Exclude tracking of any .log file in `.gitignore`
```
*.log*
```

Make a logs directory
```
mkdir logs
```

Run the Python script `logging_example.py` as below.

<details>
<summary>logging_example.py</summary>

```
import logging
from datetime import datetime

# Set Log filepath location
log_filename = f"logs/logging_example_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logs to retrieve INFO messages and higher
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename
)

logger = logging.getLogger()

logger.debug("This is a debug message")    
logger.info("System working")            
logger.warning("Something unexpected")        
logger.error("An error occurred")             
logger.critical("Critical system error")
```

</details>

##### Update our Python Script, with logging

To Do:
- Define basic logging config to create new log file
- Set logs across script at key points, or where errors can occur.
- Determine severity level for logs user the methods: info(), warning(), error() etc

Verify the error section works by setting the API_KEY to nothing in the script
```
api_key = ''
```

## Airbyte Cloud

### Introduction

[Airbyte](https://airbyte.com/) Cloud is a fully managed cloud-based data integration platform that enables users to quickly and easily extract data from various sources and load it into their desired destinations. 

It is built on the open-source Airbyte engine, designed to automate complex data pipeline tasks, simplifying data integration and freeing up engineering time for higher-value tasks.

### Sign up for Airbyte Cloud

On [Airbyte's](https://airbyte.com/) website sign up for a trial Cloud account, valid for 14 days. 

If you have already signed up for an account use your email address with a '+' after the username, e.g. will.sutton+1@email.co.uk, will.sutton+airbyte@email.co.uk

### Create a New Connection

A connection is a pipeline from a data source system, e.g. Amplitude, Mailchimp, LinkedIn to the destination location, typically a data lake or warehouse, e.g. Snowflake, Amazon S3 Bucket, Azure Blob Storage.

### Create a New Connection

### Create New Source
- Search for and select FreeAgent. However this is the production API and we have set up a Sandbox. Click the 'Fork in Builder' button on the bottom left. Use a text editor to change all instances of production URLs in the YAML to the sandbox variation.
- Configure inputs from LastPass

### Create a New Destination

Create new destination
- Set up a new destination
- Select S3 (found under marketplace)

Create a source
- Enter S3 details as follows:
    - Access Key ID: &lt;stored in LastPass&gt;
    - Secret Access Key: &lt;stored in LastPass&gt;
    - S3 Bucket Name: &lt;stored in LastPass&gt;
    - S3 Bucket Path: airbyte-sync/&lt;DESX-your-name&gt;
    - S3 Bucket Region: eu-west-2
- Set the Output Format as JSON
- Leave all other fields
- Click Set up destination
- Test destination

Select streams
- Select all relevant streams (Contacts, Invoices, Projects, Timeslips, Users)
- Sync mode: Append for all, Incremental where possible, 
i.e. "Incremental | Append", otherwise "Full refresh | Append"

Configure connection
- Schedule Type: Scheduled
- Replication frequency: Every 24 hours
- Destination Namespace (determines folder name for data stored): Custom format "YOUR-NAME"
- Sync

After 15 minutes data should start appearing in the S3 Bucket, you may need to refresh the AWS page to see data being populated. 