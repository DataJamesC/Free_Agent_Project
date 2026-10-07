# Extract Project: FreeAgent API
### Week 1 | Thursday | Instructor Led Walkthrough

## Introduction

## Learning Objectives
-- Considerations for Extracting Data
-- Introduction to Airbyte Cloud
-- Extracting with Python

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

Create a source
- Retrieve API and Secret keys from LastPass
- Set Replication Start Date to last week in date format
- Optional field, change Data region to "EU Residency Server"
- Leave all other fields as default values
- Click Set up source

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
Scripts need to start by refreshing the Access Token using the endpoint: https://api.sandbox.freeagent.com/v2/token_endpoint