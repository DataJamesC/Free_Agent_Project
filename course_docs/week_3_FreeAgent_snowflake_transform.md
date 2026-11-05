
# Transform Project: FreeAgent in Snowflake
### Week 3 | Monday | Hands-on Build Session

## Introduction

In Weeks 1 and 2 we extracted five endpoints from the FreeAgent API (contacts, users, projects, invoices and timeslips), landed them in S3 as JSON and copied them into five staging tables in Snowflake. That is our Bronze layer.

This session is about turning that Bronze layer into a layer that analysts can actually use, and then automating it so new data flows through without anyone touching it. You've should be acquianted with all of the techniques below from previous sessions. This document is a reference, not a script: how you design your schema, which refresh strategy you pick for each table, and how you automate it is up to you. Be ready to explain your decisions.

## Learning Objectives
- Flattening JSON arrays into tables
- Applying Medallion Architecture Pattern 
- Stored Procedures
  - Insert
  - Merge
  - Full Refresh
- Tasks
- Streams
- Snowpipes
- Types of Tables and views

## Before You Start

You should have the following from Week 2, all in your `<your-name>_freeagent_staging` schema:

- An external stage, `<your-name>_freeagent_python_stage`, pointing at `s3://<your-name>-freeagent-storage/python-import/`
- Five staging tables, each with a single `raw_data VARIANT` column, loaded with `COPY INTO`:
  - `stg_contacts`, `stg_users`, `stg_projects`, `stg_invoices`, `stg_timeslips`


## Recap of Existing Processes

**FreeAgent API**

- Python script to extract the five endpoints and upload them to the S3 Bucket as JSON, at `python-import/<entity>/YYYY/MM/DD/raw_<entity>.json`
- Snowflake Storage Integration and External Stage to access the files from Snowflake
- `COPY INTO` to load each endpoint into its own staging table

## Bronze-to-Silver Medallion Pipeline aka Parsing Data into a Schema

### Bronze layer review

Our Bronze layer consists of data stored as JSON. This will not be easy for data analysts, scientists or other engineers to work with, so for our silver layer, we will convert this into a schema of tables.  

```
{
  "contacts": [
    {
      "account_balance": "0.0",
      "active_projects_count": 4,
      "charge_sales_tax": "Auto",
      "contact_name_on_invoices": true,
      "country": "United Kingdom",
      "created_at": "2026-09-29T13:09:22.000Z",
      "emails_invoices_automatically": false,
      "emails_payment_reminders": false,
      "emails_thank_you_notes": false,
      "first_name": "a",
      "last_name": "b",
      "locale": "en",
      "organisation_name": "abc ltd",
      "status": "Active",
      "updated_at": "2026-09-29T13:09:22.000Z",
      "url": "https://api.sandbox.freeagent.com/v2/contacts/258815",
      "uses_contact_invoice_sequence": false,
      "uses_contact_level_email_settings": false
    },
    {
      "account_balance": "0.0",
      "active_projects_count": 9,
      "charge_sales_tax": "Auto",
      "contact_name_on_invoices": true,
      "country": "United Kingdom",
      "created_at": "2026-09-29T13:26:04.000Z",
      "email": "billing@client1.example.com",
      "emails_invoices_automatically": false,
      "emails_payment_reminders": false,
      "emails_thank_you_notes": false,
      "first_name": "Contact",
      "last_name": "1",
      "locale": "en",
      "organisation_name": "Client 1 Corp",
      "status": "Active",
      "updated_at": "2026-09-29T13:26:04.000Z",
      "url": "https://api.sandbox.freeagent.com/v2/contacts/258818",
      "uses_contact_invoice_sequence": false,
      "uses_contact_level_email_settings": false
    },
    {
      "account_balance": "0.0",
      "active_projects_count": 0,
      "charge_sales_tax": "Auto",
      "contact_name_on_invoices": true,
      "country": "United Kingdom",
      "created_at": "2026-09-29T13:34:48.000Z",
      "email": "billing@client99.example.com",
      "emails_invoices_automatically": false,
      "emails_payment_reminders": false,
      "emails_thank_you_notes": false,
      "first_name": "Contact",
      "last_name": "99",
      "locale": "en",
      "organisation_name": "Client 99 Tech",
      "status": "Active",
      "updated_at": "2026-09-29T13:34:48.000Z",
      "url": "https://api.sandbox.freeagent.com/v2/contacts/258937",
      "uses_contact_invoice_sequence": false,
      "uses_contact_level_email_settings": false
    }
  ]
}

```

Each file is a single JSON object holding one array (`contacts`, `users`, `projects`, `invoices` or `timeslips`), so each row of a staging table contains every record from that file.

Fields on a JSON object can be selected using this notation:

```
SELECT 
raw_data:"field_name"::string as field_name
FROM stg_table;
```

To turn an array into one row per record, use `LATERAL FLATTEN`. Each element of the array is returned in the `value` column, and fields are selected from that:

```
SELECT
c.value:organisation_name::string as organisation_name,
c.value:country::string as country,
c.value:account_balance::number(12,2) as account_balance
FROM stg_contacts,
LATERAL FLATTEN(input => raw_data:contacts) c;
```

Things to look out for in the FreeAgent data:

- **Relationships are URLs, not IDs.** A project's `contact` field is `https://api.sandbox.freeagent.com/v2/contacts/258818`, a timeslip's `user`, `project` and `task` fields work the same way. The number at the end of each record's own `url` is its natural ID.
- **Numbers often arrive as strings**, e.g. `"account_balance": "0.0"`, `"total_value"`, `"hours"`. Cast them.
- **Optional fields are missing rather than null**, e.g. the first contact above has no `email`. These come through as `NULL`.
- **Every extract is a full snapshot.** Each time the Python script runs, it writes every record again into a new dated folder. Once more than one file per endpoint has been loaded, the same record will appear several times in Bronze. Your Silver layer needs a strategy for this, for example keeping only the latest version of each record:

```
QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY updated_at DESC) = 1
```

Before we build our silver layer, it's important to plan it. Time to design our star (or snowflake) schema while taking into account the some possible business requirements / questions: 

- Overdue Debt & Aging: Which clients owe money, and how long has each invoice been overdue
- Payment Reliability: Which clients consistently pay late compared to their agreed payment terms?
- Monthly Cash Flow: How does total invoiced revenue compare to cash actually collected each month?

## Create Tables

For the tables in the schema we will need Unique ID fields:
- To act as a unique row identifier for each record in a table (primary key)
- To be the identifiers to connect between tables in the schema (foreign keys)

Where there is no natural key, for example a table built from a combination of fields, you'll need to create one. The functions HASH() or MD5() are standard ways of creating unique ID fields. 

### Option 1: HASH

The HASH() function will create a 64bit integer which is always assigned to the value of the field(s) you tell it to be based on, for example hashing "Belgium" leads to a HASH of -5115476029316419222. You can HASH multiple fields, hashing "Belgium" and "London" leads to a HASH of 8345500420073462720. Be careful, the order of the fields you are hashing matters. 

```
SELECT HASH(col1, col2, col3) as row_id
  , col1
  , col2
  , col3
FROM raw_data
```

This is easy to set up, now every time a combination of col1, col2, and col3 is hashed you will get the same value, meaning you can use this to create both your dimensions and fact tables independently, without needing to join them to look up the key. 

HASH IDs are fast to join on, occupy a small amount of storage, and will always recompute to the same value, i.e. the same ID. Collisions (two different inputs giving the same hash) are possible but extremely unlikely at this volume of data.

### Option 2: Dimension table + join

```
-- first build a dimension table
CREATE OR REPLACE TABLE dimensions AS
SELECT
  ROW_NUMBER() OVER (ORDER BY col1, col2, col3) as dim_id
  , col1
  , col2
  , col3
FROM (
  SELECT DISTINCT col1, col2, col3 FROM raw_data);

-- Then build fact table
SELECT d.dim_id
  , r.*
FROM raw_data r
JOIN dimensions d
ON r.col1 = d.col1
AND r.col2 = d.col2
AND r.col3 = d.col3
```

This method is more complicated and manually intensive. It requires more maintenance in the event of schema changes, i.e. new columns added. The IDs are small sequential integers, but they are not stable: when new values arrive, ROW_NUMBER() can assign different IDs on the next rebuild, so any fact table using them has to be rebuilt at the same time.


### To Do

- Decide on the tables your schema will need
- Build the tables

To update these tables on a regular basis we will use Stored Procedures.

## Stored Procedures

Overview: https://docs.snowflake.com/en/developer-guide/stored-procedure/stored-procedures-overview

Stored procedures are scripts saved in the database that you can call to perform common actions or transformations on data contained in your database. With a procedure, you can use branching, looping, and other programmatic constructs. You can reuse a procedure multiple times by calling it from other code.

Procedures can be written in SQL (Snowflake Scripting), Python and other languages. The examples in this section use SQL; there is an introduction to Python procedures in the stretch section at the end.


### Example: Rebuild the Contacts Table

The Stored Procedure below will rebuild a table containing details about Contacts. Please modify the code below for one of your tables and test it.

<details>
    <summary>Solution Procedure FreeAgent Contacts</summary>
  
```
-- Creating a Procedure : 
CREATE OR REPLACE PROCEDURE REFRESH_DIM_CONTACTS()
returns varchar
language sql
as
$$
BEGIN
    CREATE OR REPLACE TABLE DIM_CONTACTS AS
    SELECT
        CAST(REGEXP_SUBSTR(c.value:url::STRING, '/contacts/([0-9]+)$', 1, 1, 'e') AS INT) AS contact_id,
        c.value:organisation_name::STRING AS organisation_name,
        c.value:first_name::STRING AS first_name,
        c.value:last_name::STRING AS last_name,
        c.value:email::STRING AS email,
        c.value:status::STRING AS status,
        c.value:updated_at::TIMESTAMP_TZ AS updated_at
    FROM stg_contacts,
    LATERAL FLATTEN(input => raw_data:contacts) c
    -- keep only the latest version of each contact across snapshots
    QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY updated_at DESC) = 1;

    RETURN 'DIM_CONTACTS rebuilt';
END;
$$
;

--Run procedure
CALL REFRESH_DIM_CONTACTS();
```
</details>


### Insert Statements

Overview: https://docs.snowflake.com/en/sql-reference/sql/insert

For larger tables, rebuilding the entire table will be very computationally expensive. Insert can be used to add only the new data, as determined by the WHERE clause. This works well in situations where only new rows are added, i.e. tracking internet speed readings, and is less effective where values may need to be updated, i.e. an invoice moving from Draft to Paid.

Insert can also be a more efficient version of fully refreshing a table if using the OVERWRITE parameter (`INSERT OVERWRITE INTO`). This is the equivalent of truncating the table and inserting data back in, but keeps the table itself (and any grants or streams on it). This is supported by Snowflake, Databricks and BigQuery (different syntax), but not by SQL Server, MySQL or Oracle. 


### Merge Statements

Overview: https://docs.snowflake.com/en/sql-reference/sql/merge

A MERGE statement inserts, updates, and deletes values in a table that are based on values in a second table or a subquery.

```
MERGE INTO <target_table>
  USING <source>
  ON <join_expr>
  { matching / not matching criteria }
```

MERGE is the standard pattern when existing rows can change, but it has to join every incoming row against the target table, so the cost grows with the size of both. Keep the source as small as possible, for example only the new data from a stream, rather than merging the full history every time.

## Scheduling Stored Procedures

**Tasks** allow you to automate data processing. They can run at scheduled times or be triggered by events, such as when new data arrives in a stream. 

A **Stream** is an object that records changes made to tables, this includes inserts, updates and deletes. Once those actions are recorded you can use the stream as a change data capture process to trigger queries and procedures. The inserted or updated rows will be stored in the stream.  

Two things to know about streams:
- A stream only empties (its offset moves forward) when it is read by a DML statement, e.g. an `INSERT` or `MERGE` that selects from it. Simply querying it with `SELECT` does not empty it.
- Replacing the source table with `CREATE OR REPLACE TABLE` breaks the stream. `COPY INTO` and Snowpipe append to the table, so they are fine.

### Example: Procedures, Tasks and Streams

In this example we will:
- Create a Stream, to store the changes to a table
- Create a Stored Procedure that will use the Stream (You can reuse a previous procedure)
- Create a Task to run the Stored Procedure when the Stream updates 

<details>
    <summary>Stored Procedure, triggered by Task following a Stream update</summary>

```
-- Empty the table so we can see if there's an update later
TRUNCATE TABLE DIM_CONTACTS;

-- Create a Stream on the bronze table
CREATE OR REPLACE STREAM STG_CONTACTS_STREAM ON TABLE STG_CONTACTS;

-- The Stream is currently empty 
SELECT 
    metadata$action,
    metadata$isupdate,
    metadata$row_id,
    *
FROM STG_CONTACTS_STREAM;

-- A procedure that merges only the new rows from the stream into the dimension
CREATE OR REPLACE PROCEDURE MERGE_DIM_CONTACTS() 
returns varchar
language sql
as
$$
BEGIN 
    MERGE INTO DIM_CONTACTS d
    USING (
        SELECT
            CAST(REGEXP_SUBSTR(c.value:url::STRING, '/contacts/([0-9]+)$', 1, 1, 'e') AS INT) AS contact_id,
            c.value:organisation_name::STRING AS organisation_name,
            c.value:first_name::STRING AS first_name,
            c.value:last_name::STRING AS last_name,
            c.value:email::STRING AS email,
            c.value:status::STRING AS status,
            c.value:updated_at::TIMESTAMP_TZ AS updated_at
        FROM STG_CONTACTS_STREAM s, -- Stream Name
        LATERAL FLATTEN(input => s.raw_data:contacts) c
        WHERE s.metadata$action = 'INSERT'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY updated_at DESC) = 1
    ) src
    ON d.contact_id = src.contact_id
    WHEN MATCHED AND src.updated_at > d.updated_at THEN UPDATE SET
        organisation_name = src.organisation_name,
        first_name = src.first_name,
        last_name = src.last_name,
        email = src.email,
        status = src.status,
        updated_at = src.updated_at
    WHEN NOT MATCHED THEN INSERT
        (contact_id, organisation_name, first_name, last_name, email, status, updated_at)
        VALUES (src.contact_id, src.organisation_name, src.first_name, src.last_name, src.email, src.status, src.updated_at);

    RETURN 'DIM_CONTACTS merged';
END;
$$;

-- Simulate a new file arriving by duplicating a row of the bronze table
INSERT INTO STG_CONTACTS 
SELECT * FROM STG_CONTACTS
LIMIT 1;

-- Now there's 1 row in the Stream for the inserted data
SELECT 
    metadata$action,
    metadata$isupdate,
    metadata$row_id,
    *
FROM STG_CONTACTS_STREAM;

-- Create a task triggered by the stream
CREATE OR REPLACE TASK MERGE_DIM_CONTACTS_TASK
WAREHOUSE = DATASCHOOL_WH
SCHEDULE = '1 MINUTE' --this means every 1min, the task will check if the stream has data. 
WHEN SYSTEM$STREAM_HAS_DATA('STG_CONTACTS_STREAM')
as
CALL MERGE_DIM_CONTACTS();

-- Now resume the task so it starts checking the stream
ALTER TASK MERGE_DIM_CONTACTS_TASK RESUME;

--Check task has run
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE NAME = 'MERGE_DIM_CONTACTS_TASK'
ORDER BY SCHEDULED_TIME DESC;

-- Check the data has arrived
SELECT * 
FROM DIM_CONTACTS;

-- After the data has been processed it will be removed from the stream
SELECT 
    metadata$action,
    metadata$isupdate,
    metadata$row_id,
    *
FROM STG_CONTACTS_STREAM;

-- Stop Task 
ALTER TASK MERGE_DIM_CONTACTS_TASK SUSPEND;

--Check no more tasks are scheduled to run
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE NAME = 'MERGE_DIM_CONTACTS_TASK'
ORDER BY SCHEDULED_TIME DESC;
```
</details>

By default, tasks are created as suspended. The task created above will check for new data every minute, you will see it skip the procedure while SYSTEM$STREAM_HAS_DATA evaluates to FALSE (skipped runs don't use the warehouse). 

The task will check the stream every minute; if you know your data isn't loaded on a frequent basis, a task can be scheduled using cron instead.


<details>
    <summary>Schedule a task to run a procedure daily</summary>

```
-- Daily Task for contacts
CREATE OR REPLACE TASK DAILY_DIM_CONTACTS
WAREHOUSE = DATASCHOOL_WH
  SCHEDULE='USING CRON 0 8 * * * Europe/London'
AS
CALL REFRESH_DIM_CONTACTS();

-- Start Task
ALTER TASK DAILY_DIM_CONTACTS RESUME;

--Check task
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE NAME = 'DAILY_DIM_CONTACTS';

-- Stop Task 
ALTER TASK DAILY_DIM_CONTACTS SUSPEND;
```

</details>

Tasks can be chained together, so when one task completes the next will be triggered. The root task must be suspended while you add child tasks, and child tasks must be resumed before the root task (or use `SYSTEM$TASK_DEPENDENTS_ENABLE` to resume them all at once).

<details>
    <summary>Chaining tasks</summary>

```
-- Suspend the root task before adding a child to it
ALTER TASK DAILY_DIM_CONTACTS SUSPEND;

-- Runs after DAILY_DIM_CONTACTS completes. REFRESH_DIM_PROJECTS is a procedure you've built for another table
CREATE OR REPLACE TASK DAILY_DIM_PROJECTS
WAREHOUSE = DATASCHOOL_WH
  AFTER DAILY_DIM_CONTACTS
AS
CALL REFRESH_DIM_PROJECTS();

-- Resume the root task and all of its children
SELECT SYSTEM$TASK_DEPENDENTS_ENABLE('DAILY_DIM_CONTACTS');

--Check task
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE NAME IN ('DAILY_DIM_CONTACTS', 'DAILY_DIM_PROJECTS');

-- Stop Tasks (suspend the root first)
ALTER TASK DAILY_DIM_CONTACTS SUSPEND;
ALTER TASK DAILY_DIM_PROJECTS SUSPEND;
```
</details>


## Snowpipes 

Overview: https://docs.snowflake.com/en/user-guide/data-load-snowpipe-intro 

A Snowpipe automates continuous data ingestion from external storage (like Amazon S3) into Snowflake tables. Instead of loading files manually, Snowpipe runs a `COPY INTO` operation whenever new files arrive. Snowflake stores metadata about each loaded file to prevent duplicates.

Snowpipes can load data in two ways:
- On demand, by calling `ALTER PIPE ... REFRESH` or invoking the Snowpipe REST API when files are ready.
- Automatically, through event notifications from your cloud storage service (for example, AWS S3).

Event‑driven auto‑ingest is typically more efficient than frequent polling, because it charges only for file ingestion operations rather than stage checks.

Each pipe runs one `COPY INTO` statement for one table, so you'll need a pipe per staging table.

Note: Snowpipe keeps its own record of loaded files, separate from manual `COPY INTO`, so a pipe may load files you already copied in Week 2. Your snapshot handling in Silver should cope with this.

## Dynamic Tables

Overview: https://docs.snowflake.com/en/user-guide/dynamic-tables-about

Dynamic Tables are intended to be as performant as querying a table, whilst being as up to date as a view. 

Instead of writing a procedure, stream and task, you write the SELECT statement for the table you want and Snowflake keeps it up to date as the base tables change. With target lag, you control how far behind the base tables the dynamic table is allowed to fall, and therefore how often it refreshes.

Dynamic tables can be built on top of other dynamic tables. Use `TARGET_LAG = DOWNSTREAM` on the intermediate ones so they only refresh when a table that depends on them needs to.

A quick comparison of the options:

| | Kept up to date by | Query speed | Good for |
|---|---|---|---|
| Table | You (procedure, task, stream) | Fast | Full control over when and how data changes |
| View | Nothing, runs the query every time | As slow as the query | Light logic, always current |
| Dynamic Table | Snowflake, within the target lag | Fast | Declarative pipelines without managing tasks |


## Got this far with time to spare?

<details>
    <summary>Let's teach you Dynamic SQL...</summary>

Earlier we parsed our json data by writing out every field by hand. 

```
SELECT
c.value:organisation_name::string as organisation_name,
c.value:country::string as country,
c.value:account_balance::string as account_balance
FROM stg_contacts,
LATERAL FLATTEN(input => raw_data:contacts) c;
```

However, this is a very manual process, FreeAgent records have anywhere between 9 and 26 fields, and being engineers we should make the machine do the boring work. 

We can use Snowflake to write the SQL scripts for us to execute. This is called "Dynamic SQL".

Effectively it will print the SQL query you need to create the tables for your FreeAgent data source, in the form:

```
SELECT
c.value: + " column_name " + :: + data_type as " column_name ",
c.value: + " column_name " + :: + data_type as " column_name ",
c.value: + " column_name " + :: + data_type as " column_name ",
...
FROM raw_table, LATERAL FLATTEN(...) c
```

### Snowflake Python Stored Procedures

To run the SQL that Snowflake writes for us, we'll use a Python stored procedure.

A Snowflake Python stored procedure is wrapped in a function taking the snowpark_session and any arguments you have given as options. The snowpark_session will give you access to execute SQL queries through Python. 

i.e. .collect() will execute a provided script.
```
my_sql_query = "SELECT CURRENT_DATE() as today;"
query_result = snowpark_session.sql(my_sql_query).collect()
```

Let's create this as a stored procedure

```
CREATE OR REPLACE PROCEDURE TODAY()
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES=('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
def run(snowpark_session):
    my_sql_query = "SELECT CURRENT_DATE() as today;"
    query_result = snowpark_session.sql(my_sql_query).collect()
    return query_result
$$;
```

Then we can run our procedure with 

```
CALL TODAY();
```

The objects returned from a query are returned as a list of Row objects

[Row(TODAY=datetime.date(2025, 5, 21))]

We can extract the exact value using [0] to select the first row and ['TODAY'] to select the column. Recreate the procedure selecting the value from your result to verify this works.

```
CREATE OR REPLACE PROCEDURE TODAY()
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES=('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
def run(snowpark_session):
    my_sql_query = "SELECT CURRENT_DATE() as today;"
    query_result = snowpark_session.sql(my_sql_query).collect()
    query_result = query_result[0]['TODAY']
    return query_result
$$;

CALL TODAY();
```

Similar to functions we can add arguments to our procedures:
- in the CREATE step `CREATE OR REPLACE PROCEDURE TODAY(argument data_type)`
- and in the run(snowpark_session, argument):

In our example add an argument to the procedure and return a string to the user

```
CREATE OR REPLACE PROCEDURE TODAY(NAME STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES=('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
def run(snowpark_session, NAME):
    my_sql_query = "SELECT CURRENT_DATE() as today;"
    query_result = snowpark_session.sql(my_sql_query).collect()
    query_result = query_result[0]['TODAY']

    user_name = NAME
    today_str = str(query_result)
    message = f"Hey {user_name} it is {today_str} today"
    
    return message
$$;

CALL TODAY('Will');
```

### Dynamic SQL Stored Procedure

The procedure below takes a staging table and the name of the array inside it, works out every field and its data type, then writes and runs the `CREATE TABLE` statement for you. It returns the SQL it ran so you can check it.

<details>
    <summary>Dynamic SQL Stored Procedure</summary>

```
CREATE OR REPLACE PROCEDURE GENERATE_FLATTENED_TABLE(SOURCE_TABLE_NAME VARCHAR, ARRAY_KEY VARCHAR, DESTINATION_TABLE_NAME VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
def run(snowpark_session, source_table_name, array_key, destination_table_name):
    # One row per record in the array, e.g. raw_data:contacts
    from_sql = f"{source_table_name} t, LATERAL FLATTEN(input => t.raw_data:{array_key}) r"

    # Find every field and its data type(s) across all records.
    # Fields that are always null become VARCHAR, fields with mixed types or nested objects are skipped.
    get_columns_sql = f"""
        SELECT
            f.key AS column_name,
            LISTAGG(DISTINCT CASE WHEN TYPEOF(f.value) = 'NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END, ', ') AS data_type
        FROM {from_sql},
        LATERAL FLATTEN(input => r.value) f
        GROUP BY f.key
        HAVING data_type NOT IN ('OBJECT', 'ARRAY') AND data_type NOT LIKE '%,%'
    """
    columns = snowpark_session.sql(get_columns_sql).collect()

    if not columns:
        return f"No flattenable columns found in {source_table_name} for array '{array_key}'"

    select_cols = [
        f'r.value:"{row["COLUMN_NAME"]}"::{row["DATA_TYPE"]} AS "{row["COLUMN_NAME"]}"'
        for row in columns
    ]
    column_list_separator = ",\n    "

    create_table_sql = f"""CREATE OR REPLACE TABLE {destination_table_name} AS
SELECT
    {column_list_separator.join(select_cols)}
FROM {from_sql};"""

    snowpark_session.sql(create_table_sql).collect()

    # Return the executed SQL for verification
    return create_table_sql
$$;

CALL GENERATE_FLATTENED_TABLE('stg_contacts', 'contacts', 'GEN_CONTACTS');
```
</details>

---
<details>
    <summary>Workings of how the Dynamic SQL Stored Procedure is built, you don't need to understand this it's just if you're interested</summary>

Using Snowflake, we can find all the keys used across the records in an array. The first FLATTEN turns the array into one row per record, the second turns each record into one row per field.

```
SELECT DISTINCT 
    f.key AS column_name
FROM stg_contacts t,
  LATERAL FLATTEN(input => t.raw_data:contacts) r,
  LATERAL FLATTEN(input => r.value) f
ORDER BY f.key;
```

We can then have SQL dynamically write these columns as a SQL script for us to execute.

```
WITH CTE as (
    SELECT DISTINCT 
        f.key AS column_name
    FROM stg_contacts t,
      LATERAL FLATTEN(input => t.raw_data:contacts) r,
      LATERAL FLATTEN(input => r.value) f
)

SELECT 
  'SELECT r.value:' || LISTAGG(DISTINCT '"' || column_name || '"', ',\nr.value:') || 
  '\nFROM stg_contacts t, LATERAL FLATTEN(input => t.raw_data:contacts) r;' AS generated_sql
FROM CTE;
```

Run the SQL generated by this query. Every column comes out as a VARIANT, so next we need data types.

**How do we find each field's data type?**

The `TYPEOF()` function will return the data type of each value, including `OBJECT` and `ARRAY` for anything nested. 

```
-- Determine data types for each field
SELECT DISTINCT 
    f.key AS column_name,
    TYPEOF(f.value) as data_type
FROM stg_contacts t,
  LATERAL FLATTEN(input => t.raw_data:contacts) r,
  LATERAL FLATTEN(input => r.value) f
ORDER BY f.key;
```
We can ensure we have consistent data types in our tables with `LISTAGG(DISTINCT TYPEOF(f.VALUE),', ')` to comma separate any multi data types columns.

To remove any nested objects or arrays and any mixed-type fields, we filter out `OBJECT`, `ARRAY` and anything LIKE `%,%`.

As we are constructing a SELECT statement, we will want to include the data types. `NULL_VALUE` is not a valid data type so we will convert these to `VARCHAR`.

This query will return 2 columns with the column names and the data types.

```
SELECT 
    f.key as column_name,
    LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
FROM stg_contacts t,
  LATERAL FLATTEN(input => t.raw_data:contacts) r,
  LATERAL FLATTEN(input => r.value) f
GROUP BY f.key
HAVING (data_type NOT IN ('OBJECT','ARRAY')
AND data_type NOT LIKE '%,%');
```

Now we will need to construct a CREATE TABLE statement SELECTing from our raw table, combining all of these columns into one cell with LISTAGG()

```
WITH CONTACT_COLUMNS as (
SELECT 
    f.key as column_name,
    LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
FROM stg_contacts t,
  LATERAL FLATTEN(input => t.raw_data:contacts) r,
  LATERAL FLATTEN(input => r.value) f
GROUP BY f.key
)
SELECT 
'CREATE OR REPLACE TABLE gen_contacts AS  \n' ||
'SELECT \n' ||
LISTAGG(DISTINCT 'r.value:"' || column_name || '"::' || data_type || ' as "' || column_name || '"', ',\n') ||
'\nFROM stg_contacts t, LATERAL FLATTEN(input => t.raw_data:contacts) r;' as generated_sql
FROM CONTACT_COLUMNS
WHERE (data_type NOT IN ('OBJECT','ARRAY')
AND data_type NOT LIKE '%,%');
```

The same query works for any of our endpoints by changing:
- the staging table, e.g. `stg_invoices`
- the array name in `LATERAL FLATTEN(input => t.raw_data:invoices)`
- the table name in `CREATE OR REPLACE TABLE gen_invoices AS`

The stored procedure above wraps this query, swapping those three values for its arguments.

</details>

---

### To do

1. Call `GENERATE_FLATTENED_TABLE` for each of your five staging tables and check the SQL it returns.
2. The generated tables are a straight copy of the JSON: URLs are still URLs, numbers stored as text are still text and snapshots are still duplicated. Decide whether you'd fix these by extending the procedure or by building on top of the generated tables.
3. Bonus: automate your generated tables with a stream and task. Remember the procedure the task calls must read from the stream in a DML statement, otherwise the stream never empties and the task will run every time it's scheduled.

</details>

## Appendix

### References

Snowflake Storage Integration

- S3: https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration
- Azure: https://docs.snowflake.com/en/user-guide/data-load-azure-config

Snowpipe
- Snowflake: https://docs.snowflake.com/en/user-guide/data-load-snowpipe-intro
- CREATE PIPE: https://docs.snowflake.com/en/sql-reference/sql/create-pipe
- Amazon S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-event-notifications.html

  
Snowflake Stored Procedures: https://docs.snowflake.com/en/developer-guide/stored-procedure/stored-procedures-overview

Tasks in Snowflake: https://docs.snowflake.com/en/user-guide/tasks-intro

Streams in Snowflake: https://docs.snowflake.com/en/user-guide/streams-intro

FLATTEN: https://docs.snowflake.com/en/sql-reference/functions/flatten

Dynamic Tables: https://docs.snowflake.com/en/user-guide/dynamic-tables-about
