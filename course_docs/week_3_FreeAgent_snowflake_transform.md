
# Transform Project: Amplitude in Snowflake
### Week 3 | Monday | Instructor Led Walkthrough

## Introduction

## Learning Objectives
- Dealing with nested arrays
- Applying Medallion Architecture Pattern 
- Stored Procedures
  - Insert
  - Merge
  - Full Refresh
- Tasks
- Streams
- Snowpipes
- Types of Tables and views

## Recap of Existing Processes

**Amplitude Export API** 

- Python script to extract and upload data to S3 Bucket as JSON
- Snowflake Storage Integration to query raw data in Snowflake

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

Typically, the JSON structures can be parsed into a table using these selectors:

```
SELECT 
json_data:"account_balance"::string as "$account_balance",
json_data:"country"::string as "country"
FROM raw_table;
```

And fields from nested arrays can be accessed as:

```
SELECT
json_data:array_name:field_name::data_type as new_field_name
FROM table
```


Before we built our silver layer, it's important to plan it. Time to build our snowflake schema while taking into account the business requirements / questions: 

- Overdue Debt & Aging: Which clients owe money, and how long has each invoice been overdue
- Payment Reliability: Which clients consistently pay late compared to their agreed payment terms?
- Monthly Cash Flow: How does total invoiced revenue compare to cash actually collected each month?

## Create Tables

For the tables in the schema we will need to create Unique ID fields:
- To act as a unique row identifier for each record in a table (primary key)
- To be the identifiers to connect between tables in the schema (foreign keys)

The functions HASH() or MD5() are standard ways of creating a unique ID fields. 

### Option 1: HASH

The HASH() function will create a 64bit integer which is always assigned to the value of the field(s) you tell it to be based on, for example hashing "Belgium" leads to a HASH of -5115476029316419222. You can HASH multiple fields, hashing "Belgium" and "London" leads to a HASH of 8345500420073462720. Be careful, the order of the fields you are hashing matters. 

```
SELECT HASH(col1, col2, col3) as event_id
  , col1
  , col2
  , col3
FROM raw_data
```

This is easy to set up, now everytime a combination of col1, col2, and col3, is hashed you will get the same value, meaning you can use this to create both your dimensions and fact tables. 

HASH ids are very fast performing for joins, whilst occupying a small amount of much storage, and will always recomputes to the same value, i.e. the same ID. The costs for a HASH are on the compute side.

### Option 2: Dimension table + join

```
-- first build a dimension table
CREATE OR REPLACE TABLE dimensions AS
SELECT
  ROW_NUMBER() OVER (Order BY col1, col2, col3) as event_id
  , col1
  , col2
  , col3
FROM (
  Select DISTINCT col1, col2, col3 FROM raw_data);

-- Then build fact table
SELECT r.*
  , d.event_id
  , r.col1
  , r.col2
  , r.col3
from r.raw_data
JOIN d.dimensions
ON r.col1 = d.col1
AND r.col2 = d.col2
AND r.col3 = d.col3
```

This method is more complicated and manually intensive. It requires more maintenance in the event of schema changes, i.e. new columns added. There would be a slight improvement in join performance over hash due to a smaller ID range created by ROW_NUMBER(). 


### To Do

- Decide on the tables your schema will need
- Build the tables

To update these tables on a regular basis we will use Stored Procedures.

## Stored Procedures

Overview: https://docs.snowflake.com/en/developer-guide/stored-procedure/stored-procedures-overview

Stored procedures are scripts saved in the database that you can call to perform common actions or transformations on data contained in your database. With a procedure, you can use branching, looping, and other programmatic constructs. You can reuse a procedure multiple times by calling it from other code.

A Snowflake stored procedure code is wrapped in a function taking the snowpark_session and any arguments you have given as options. The snowpark_session will give you access to execute SQL queries through Python.


### Example: Rebuild the Contacts Table

The Stored Procedure below will rebuild a table containing details about Contacts. Please modify the code below for one of your tables and test it.

<details>
    <summary>Solution Procedure FreeAgent Contacts</summary>
  
```
-- Creating a Procedure : 
CREATE OR REPLACE PROCEDURE REFRESH_CONTACTS()
returns varchar
language sql
as
$$
CREATE OR REPLACE TABLE FREEAGENT_ANALYTICS.DIM_CONTACTS   AS
SELECT
    CAST(REGEXP_SUBSTR(c.value:url::STRING, '/contacts/([0-9]+)$', 1, 1, 'e') AS INT) AS contact_id,
    c.value:organisation_name::STRING AS organisation_name,
    c.value:first_name::STRING AS first_name,
    c.value:last_name::STRING AS last_name,
FROM stg_contacts,
LATERAL FLATTEN(input => raw_data:contacts) c;
$$
;

--Run procedure
CALL REFRESH_CONTACTS();
```
</details>


### Insert Statements

Overview: https://docs.snowflake.com/en/sql-reference/sql/insert

For larger tables, rebuilding the entire table will be very computationally expensive. Insert here can be used to add only the new data in determined by the WHERE clause. This works well in situations where only new rows are added, i.e. tracking internet speed readings, less effective where values may need to be updated, i.e. an order is returned.

Insert Into can also be a more efficient version of fully refreshing a table if using the Overwrite parameter. This is the equivalent of truncating the table and inserting data back in. This is supported by Snowflake, Databricks and Bigquery (different syntax), but not by SQLServer, MySQL or Oracle. 


### Merge Statements

Overview: https://docs.snowflake.com/en/sql-reference/sql/merge

A MERGE statement inserts, updates, and deletes values in a table that are based on values in a second table or a subquery.

```
MERGE INTO <target_table>
  USING <source>
  ON <join_expr>
  { matching / not matching criteria }
```

This is very heavy to compute as it has to process every single row of the data. 

Remember this compute power instensive and should be reserved for cases of a small amount of rows that need updating regularly.  

## Scheduling Stored Procedures

**Tasks** allow you to automate data processing. They can run at scheduled times or be triggered by events, such as when new dat arrives in a stream. 

A **Stream** is an object that records changes made to tables, this includes inserts, updates and deletes. Once those actions are recorded you can use the stream as a change data capture process to trigger queries and procedures. The inserted or updated rows will be stored in the stream.  

### Example: Procedures, Tasks and Streams

In this example we will:
- Create a Stream, to store the changes to a table
- Create a Stored Procedure that will use the Stream (You can reuse a previous procedure)
- Create a Task to run the Stored Procedure when the Stream updates 

<details>
    <summary>Stored Procedure, triggered by Task following a Stream update</summary>

```
CREATE OR REPLACE TABLE S_AMPLITUDE_COUNTRY AS 
SELECT DISTINCT
    "country" as country_name,
    hash("country") as country_id
FROM EVENTS_TABLE;

-- Empty the table so we can see if there's an update later
TRUNCATE TABLE S_AMPLITUDE_COUNTRY;

-- Create a Stream 
CREATE OR REPLACE STREAM AMPLITUDE_RAW ON TABLE EVENTS_TABLE;

-- The Stream is currently empty 
SELECT 
    metadata$action,
    metadata$isupdate,
    metadata$row_id,
    *
FROM AMPLITUDE_RAW;

-- Modifying our Country Procedure: 
CREATE OR REPLACE PROCEDURE REFRESH_S_AMPLITUDE_COUNTRY() 
returns varchar
language sql
as
$$
BEGIN 

INSERT INTO S_AMPLITUDE_COUNTRY
SELECT DISTINCT
"country" as country_name,
hash("country") as country_id
FROM AMPLITUDE_RAW; -- Stream Name
END
$$;

-- Inserting 2 rows via duplication
INSERT INTO EVENTS_TABLE ( 
SELECT * FROM AMPLITUDE_EVENTS_RAW
LIMIT 2);

-- Now there's 2 rows row in the Stream for the inserted data
SELECT 
    metadata$action,
    metadata$isupdate,
    metadata$row_id,
    *
FROM AMPLITUDE_RAW;

-- Create a task triggered by the stream
CREATE OR REPLACE TASK TRIGGER_S_AMPLITUDE_EVENTS_REFRESH
WAREHOUSE = DATASCHOOL_WH
SCHEDULE = '1 MINUTE' --this means every 1min, the task will check if the stream has data. 
WHEN SYSTEM$STREAM_HAS_DATA('AMPLITUDE_RAW')
as
CALL REFRESH_S_AMPLITUDE_COUNTRY();

-- Now set the task as resume to start checking the stage
ALTER TASK TRIGGER_S_AMPLITUDE_EVENTS_REFRESH RESUME;

--Check task has run
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY());

-- Check the data has arrived
SELECT * 
FROM S_AMPLITUDE_COUNTRY;

-- After the data has been processed it will be removed from the stage
SELECT 
    metadata$action,
    metadata$isupdate,
    metadata$row_id,
    *
FROM AMPLITUDE_RAW;

-- Stop Task 
ALTER TASK TRIGGER_S_AMPLITUDE_EVENTS_REFRESH SUSPEND;

--Check no more tasks are scheduled to run
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY());
```
</details>

By default, tasks created are set as suspended. The task created above will check for new data every minute, you will see them skip the procedure as SYSTEM$STREAM_HAS_DATA will evaluate to FALSE. 

The stream will look for data every minute, if you know your data isn't loaded on a frequent basis a task can be scheduled using cron.

Schedule a tasks to run a procedure daily


<details>
    <summary>Schedule a tasks to run a procedure daily</summary>

```
-- Daily Task for country 
CREATE TASK DAILY_S_AMPLITUDE_COUNTRY
WAREHOUSE = dataschool_wh
  SCHEDULE='USING CRON 0 8 * * * Europe/London'
AS
CALL REFRESH_S_AMPLITUDE_COUNTRY();

-- Start Task
ALTER TASK DAILY_S_AMPLITUDE_COUNTRY RESUME;

--Check task
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY());

-- Stop Task 
ALTER TASK DAILY_S_AMPLITUDE_COUNTRY SUSPEND;
```

</details>

Tasks can be chained together, so when one task completes the next will be triggered. 

<details>
    <summary> Chaining of tasks task </summary>

```
CREATE OR REPLACE TASK DAILY_G_AMPLITUDE
WAREHOUSE = dataschool_wh
  AFTER DAILY_S_AMPLITUDE_COUNTRY
AS
SELECT * FROM S_AMPLITUDE_COUNTRY; 

-- Start Task
ALTER TASK DAILY_G_AMPLITUDE RESUME;

--Check task
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY());

-- Stop Task 
ALTER TASK DAILY_G_AMPLITUDE SUSPEND;
```
</details>


## Snowpipes 

Overview: https://docs.snowflake.com/en/user-guide/data-load-snowpipe-intro 

A Snowpipe automates continuous data ingestion from external storage (like Amazon S3) into Snowflake tables. Instead of loading files manually, Snowpipe runs a `COPY INTO` operation whenever new files arrive. Snowflake stores metadata about each loaded file to prevent duplicates.

Snowpipes can load data in two ways:
- On demand, by calling `ALTER PIPE ... REFRESH` or invoking the Snowpipe REST API when files are ready.
- Automatically, through event notifications from your cloud storage service (for example, AWS S3).

Event‑driven auto‑ingest is typically more efficient than frequent polling, because it charges only for file ingestion operations rather than stage checks.

### Example: Build a Snowpipe for the Bronze Layer

<details>
    <summary> Solution to creating a snowpipe from your stage</summary>

```
CREATE OR REPLACE PIPE <your-name>-amplitude_snowpipe
auto_ingest = TRUE
as 
COPY INTO AMPLITUDE_EVENTS
FROM @TIL_DATA_ENGINEERING.<your-schema>.AMPLITUDE_AIRBYTE_ST/events/
FILE_FORMAT = TIL_DATA_ENGINEERING.<your-schema>.<your-name>_JSON_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'CONTINUE';

-- Set your Snowpipe to look for new files
ALTER PIPE <your-name>-amplitude_snowpipe REFRESH; 

-- Check your pipe status
SELECT SYSTEM$PIPE_STATUS('<your-name>-amplitude_snowpipe') AS pipe_status;

-- Check your pipe's upload history
SELECT *
FROM INFORMATION_SCHEMA.PIPE_USAGE_HISTORY
WHERE PIPE_NAME = '<your-name>-amplitude_snowpipe';
```
</details>

### Event‑driven Snowpipe with AWS S3 (Auto‑ingest)

Overview: https://docs.snowflake.com/en/user-guide/data-load-snowpipe-auto-s3

To enable Snowflake to automatically load data as soon as files appear in your S3 bucket, use the **auto_ingest** option. This feature uses Amazon SQS notifications to trigger Snowpipe.


Create a pipe with `AUTO_INGEST = TRUE`
```
CREATE OR REPLACE PIPE <your-name>_amplitude_snowpipe_sqs
AUTO_INGEST = TRUE
as 
COPY INTO AMPLITUDE_EVENTS
FROM @TIL_DATA_ENGINEERING.<your-schema>.AMPLITUDE_AIRBYTE_ST/events/
FILE_FORMAT = TIL_DATA_ENGINEERING.<your-schema>.<your-name>_JSON_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'CONTINUE';
```

Configure event notifications for your S3 bucket to notify Snowpipe when new data is available to load. The auto-ingest feature relies on Amazon SQS queues to deliver event notifications from S3 to Snowpipe.

Amazon SQS (Simple Queue Service) is a managed message queuing service from AWS that enables you to decouple and communicate between different parts of your application.

For ease of use, Snowpipe SQS queues are created and managed by Snowflake. The SHOW PIPES command output displays the Amazon Resource Name (ARN) of your SQS queue, in the column notification_channel.

```
SHOW PIPES;
```
In the output, locate the `NOTIFICATION_CHANNEL` field—this contains the SQS ARN created by Snowflake.

### Log in to the Amazon S3 console.

In the AWS S3 console (or using Terraform/CLI), create an event notification for your S3 bucket.

Choose Your Bucket > Properties > Event Notifications > Create a New Event Notification

- Name: Name of the event notification (e.g. Ingest Snowflake).
- Events: Select the ObjectCreate (All) option.
- Destination: Select the SQS Queue from the dropdown list.
- SQS queue ARN: Paste the SQS queue name from the Snowflake SHOW PIPES output.
- Event types: All object create events

Snowpipe with SQS ingest is now configured.

Load more files to AWS S3 and verify it has worked by. 

A simple count before and after loading files will verify new files have been added.

```
SELECT COUNT(*) FROM amplitude_events_raw_python;
```

Check the status of your pipe and look for updated values in `lastReceivedMessageTimestamp`
```
SELECT SYSTEM$PIPE_STATUS('<your-name>_amplitude_snowpipe_sqs');
```

## Dynamic Tables

Overview: https://docs.snowflake.com/en/user-guide/dynamic-tables-about

Dynamic Tables are intended to be as performant as a querying a table, whilst being as up to date as a view. 

The Dynamic Table will refresh when the base tables are refreshed. Usually, the table data freshness won’t be more than that far behind the base table data freshness. With target lag, you control how often the table refreshes and how up-to-date the data stays. 

<img src="images/snowflake_dynamic_tables.png">


## Got this far with time to spare?

<details>
    <summary>Let's teach you Dynamic SQL...</summary>

Earlier we parsed our json data using the notation. 

```
SELECT 
json_data:"$insert_id"::string as "$insert_id",
json_data:"$insert_key"::string as "$insert_key",
json_data:event_properties
FROM amplitude_events_raw;
```

However, this is a very manual process, and being engineers we should make the machine do the boring working. 

We can use Snowflake to write the SQL scripts for use to execute. This is called "Dynamic SQL".

Effectively it will print the SQL query you need to create the tables for your Amplitude data source, in the form:

```
SELECT
json_data: + " column_name " + :: + data_type as " column_name ",
json_data: + " column_name " + :: + data_type as " column_name ",
json_data: + " column_name " + :: + data_type as " column_name ",
...
FROM raw_table
```

<details>
    <summary>Dynamic SQL Stored Procedure</summary>

```
CREATE OR REPLACE PROCEDURE GENERATE_FLATTENED_JSON(SOURCE_TABLE_NAME VARCHAR, NESTED_JSON_PATH VARCHAR, DESTINATION_TABLE_NAME VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'generate_flattened_json_sql_python'
AS
$$
import snowflake.snowpark as snowpark
from snowflake.snowpark.types import Variant, StringType, IntegerType, BooleanType, FloatType
from snowflake.snowpark.functions import col, object_construct, table_function, lit

def generate_flattened_json_sql_python(
    session: snowpark.Session,
    source_table_name: str,
    nested_json_path: str,
    destination_table_name: str
) -> str:
    """
    Dynamically generates and executes SQL to flatten JSON data from a source table
    into a new destination table in Snowflake using Snowpark.

    Args:
        session (snowpark.Session): The Snowpark session object.
        source_table_name (str): The fully qualified name of the source table
                                 (e.g., 'DATABASE.SCHEMA.TABLE').
        nested_json_path (str): The dot-separated path to the nested JSON object
                                 to flatten (e.g., 'event_properties', 'user_properties').
                                 Use an empty string or None to flatten the top-level 'json_data'.
        destination_table_name (str): The name of the table to create or replace
                                      with the flattened data.

    Returns:
        str: A message indicating the success or failure of the operation,
             including the generated SQL.
    """
    sql_query_get_columns = ""
    json_input_path_sql = ""
    create_table_select_cols = []
    create_table_sql = ""
    where_clause = ""

    try:
        # 1. Determine the base JSON path for flattening
        # If NESTED_JSON_PATH is null or empty, target the top-level json_data.
        # Otherwise, target the specific nested path within json_data.
        if nested_json_path is None or nested_json_path == '':
            json_input_path_sql = "json_data"
            where_clause = "" # No specific WHERE clause for top-level flattening
        else:
            json_input_path_sql = f"json_data:{nested_json_path}"
            # For nested tables, add event_id and session_id to link back to the main events.
            create_table_select_cols.append("json_data:event_id::INT AS event_id")
            create_table_select_cols.append("json_data:session_id::INT AS session_id")
            # Add a WHERE clause to filter out rows where the nested JSON object is null or empty.
            where_clause = f"WHERE {json_input_path_sql} IS NOT NULL AND {json_input_path_sql} <> PARSE_JSON('{{}}')"

        # 2. Construct the SQL query to fetch distinct column names and their data types
        # from the specified JSON path using Snowpark DataFrame operations.
        # This approach leverages the Snowflake `FLATTEN` table function and `TYPEOF` SQL function.
        # It then groups by key and aggregates types to identify mixed types or non-scalar types.
        sql_query_get_columns = f"""
            SELECT
                f.key as column_name,
                LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
            FROM {source_table_name} t,
            LATERAL FLATTEN(input => t.{json_input_path_sql}) f
            GROUP BY f.key
            HAVING (data_type NOT IN ('OBJECT','ARRAY') AND data_type NOT LIKE '%,%');
        """

        # Execute the query to get the metadata for the columns.
        column_metadata_df = session.sql(sql_query_get_columns).collect()

        # 3. Iterate through the results to build the SELECT column list for the new table.
        if not column_metadata_df:
            return "No flattenable columns found for the given JSON path, or the path does not exist/contains only objects/arrays."

        for row in column_metadata_df:
            col_name = row["COLUMN_NAME"]
            data_type = row["DATA_TYPE"]

            # Determine the prefix for accessing the JSON key.
            # For top-level, it's just 'json_data', for nested it's 'json_data:nested_path'.
            projection_prefix = "json_data" if nested_json_path is None or nested_json_path == '' else f"json_data:{nested_json_path}"

            # Escape column names that might be Snowflake reserved keywords or contain special characters
            # to ensure they are valid SQL identifiers in the alias.
            escaped_col_name = f'"{col_name}"'

            # Add the column projection string (e.g., json_data:"key"::VARCHAR AS "key") to the list.
            # We use `session.sql` and string concatenation for the dynamic SQL, similar to JS SP.
            create_table_select_cols.append(f'{projection_prefix}:"{col_name}"::{data_type} AS {escaped_col_name}')

        # Define the separator for joining column select statements outside the f-string
        column_list_separator = ',\n            '

        # 4. Construct the final CREATE OR REPLACE TABLE statement.
        create_table_sql = f"""
CREATE OR REPLACE TABLE {destination_table_name} AS
SELECT
            {column_list_separator.join(create_table_select_cols)}
FROM {source_table_name}
{where_clause};
        """

        # 5. Execute the generated SQL to create the new flattened table.
        session.sql(create_table_sql).collect()

        # Return a success message including the executed SQL for verification.
        return f"{create_table_sql}"

    except Exception as e:
        # Catch any errors during the procedure execution and return an error message.
        return f"Failed to execute procedure: {e}\nSQL tried: {sql_query_get_columns}\nFinal SQL attempted: {create_table_sql}"
$$;
```
</details>

---
<details>
    <summary>Workings of how I built the Dynamic SQL Stored Procedure, you don't need to understand this it's just if you're interested</summary>

Using Snowflake, we can find all the top-level keys from this table.

```
SELECT DISTINCT 
    f.VALUE AS top_key
FROM amplitude_events_raw as t,
  LATERAL FLATTEN(
    INPUT => OBJECT_KEYS(t.json_data)  
  ) f
ORDER BY f.VALUE;
```


We can then have SQL dynamically write these columns as a SQL script for us to execute.

```
WITH CTE as (
    SELECT DISTINCT 
        f.VALUE AS top_key
    FROM amplitude_events_raw as t,
      LATERAL FLATTEN(
        INPUT => OBJECT_KEYS(t.json_data)  -- returns ARRAY of top-level keys
      ) f
)

SELECT 
  'SELECT json_data:' || LISTAGG(DISTINCT '"' ||  top_key || '"', ',\njson_data:') || 
  ' FROM amplitude_events_raw;' AS generated_sql
FROM CTE;
```

Run the SQL generated by this query, you'll notice there are some nested arrays, e.g. user_properties. 

For our schema, we'd like to separate these nested arrays into their own tables. 

**How do we identify what's a nested array?**

The `TYPEOF()` function will determine OBJECTS as arrays, which we can find. 

```
-- Determine data types for top keys
WITH CTE as (
    SELECT DISTINCT 
        f.key AS top_key,
        TYPEOF(f.VALUE) as data_type
        FROM amplitude_events_raw as t,
        LATERAL FLATTEN(input => t.json_data) f
)

SELECT *
FROM CTE;
```
We can ensure we have consistent data types in our tables with `LISTAGG(DISTINCT TYPEOF(f.VALUE),', ')` to comma separate any multi data types columns.

To remove any nested json arrays we filter out `OBJECT`, `ARRAY` and anything LIKE `%,%`.

As we are constructing a SELECT statement, we will want to include the data types in the form, `NULL_VALUE` is not a valid data type so we will convert these to `VARCHAR`

```
SELECT
json_data: + " column_name " + :: + data_type as " column_name ",
json_data: + " column_name " + :: + data_type as " column_name ",
json_data: + " column_name " + :: + data_type as " column_name ",
...
FROM raw_table
```

This query will return a 2 columns with the column_names and the data types.

```
SELECT 
    f.key as column_name,
    LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
  FROM amplitude_events_raw t,
  LATERAL FLATTEN(input => t.json_data) f
  GROUP BY f.key
)
SELECT 
*
FROM EVENT_COLUMNS
WHERE (data_type NOT IN ('OBJECT','ARRAY')
AND data_type NOT LIKE '%,%');
```

Now we will need to construct a CREATE TABLE statement SELECTing from our raw table, combining all of these columns into one cell with LISTAGG()

```
WITH EVENT_COLUMNS as (
SELECT 
    f.key as column_name,
    LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
  FROM amplitude_events_raw t,
  LATERAL FLATTEN(input => t.json_data) f
  GROUP BY f.key
)
SELECT 
'CREATE OR REPLACE TABLE events AS  \n' ||
'SELECT \n' ||
LISTAGG(DISTINCT 'json_data:"' ||column_name || '"::' || data_type || ' as "' ||column_name || '"', ',\n') ||
'\nFROM amplitude_events_raw;' as generated_sql
FROM EVENT_COLUMNS
WHERE (data_type NOT IN ('OBJECT','ARRAY')
AND data_type NOT LIKE '%,%')
```

We can also use a similar query to extract data from the nested objects by changing out `LATERAL FLATTEN()`

```
-- Extract user properties
WITH EVENT_COLUMNS as (
SELECT 
    f.key as column_name,
    LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
  FROM amplitude_events_raw t,
  LATERAL FLATTEN(input => t.json_data:user_properties) f
  GROUP BY f.key
)
SELECT 
'CREATE OR REPLACE TABLE user_properties AS  \n' ||
'SELECT \n' ||
'json_data:event_id::INTEGER AS event_id, \n' ||
'json_data:session_id::INTEGER AS session_id, \n' ||
LISTAGG(DISTINCT 'json_data:user_properties."' ||column_name || '"::' || data_type || ' as "' ||column_name || '"', ',\n') ||
'\nFROM amplitude_events_raw
WHERE json_data:user_properties <> ''{}'';' as generated_sql
FROM EVENT_COLUMNS
WHERE (data_type NOT IN ('OBJECT','ARRAY')
AND data_type NOT LIKE '%,%');
```

What's changed:
- In the CTE `LATERAL FLATTEN(input => t.json_data:user_properties)`
- Columns now are called with `'json_data:user_properties."' instead of just 'json_data:'`
- We are filtering empty json out `WHERE json_data:user_properties <> ''{}''`
- And changed our table name `CREATE OR REPLACE TABLE user_properties AS`
- Add references so we can join back to the events table

```
json_data:event_id::INTEGER AS event_id, \n' ||
'json_data:session_id::INTEGER AS session_id, \n' ||
```
These will act as a composite foreign key

##### Logic for Table paths

In the procedure below we pass the table name as an argument, this can come in many forms:
- table_name
- schema.table_name
- database.schema.table_name

What the logic below does is identify which version of table name we have and then added the current path if a schema or database is not speficied, returning `fully_qualified_table` which is the full path.

```
parts = TABLE_NAME.split('.')
    if len(parts) == 1:  # Just table name provided
        current_db = snowpark_session.sql("SELECT CURRENT_DATABASE() AS DB").collect()[0]['DB']
        current_schema = snowpark_session.sql("SELECT CURRENT_SCHEMA() AS SCHEMA").collect()[0]['SCHEMA']
        fully_qualified_table = f"{current_db}.{current_schema}.{TABLE_NAME}"
    elif len(parts) == 2:  # Schema.table provided
        current_db = snowpark_session.sql("SELECT CURRENT_DATABASE() AS DB").collect()[0]['DB']
        fully_qualified_table = f"{current_db}.{TABLE_NAME}"
    else:  # Fully qualified name provided
        fully_qualified_table = TABLE_NAME
```

Create a stored procedure for events table.

```
CREATE OR REPLACE PROCEDURE UPDATE_EVENTS_TABLE(TABLE_NAME STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES=('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
def run(snowpark_session, TABLE_NAME):

    # Handle table name - if it doesn't include database/schema, use current ones
    parts = TABLE_NAME.split('.')
    if len(parts) == 1:  # Just table name provided
        current_db = snowpark_session.sql("SELECT CURRENT_DATABASE() AS DB").collect()[0]['DB']
        current_schema = snowpark_session.sql("SELECT CURRENT_SCHEMA() AS SCHEMA").collect()[0]['SCHEMA']
        fully_qualified_table = f"{current_db}.{current_schema}.{TABLE_NAME}"
    elif len(parts) == 2:  # Schema.table provided
        current_db = snowpark_session.sql("SELECT CURRENT_DATABASE() AS DB").collect()[0]['DB']
        fully_qualified_table = f"{current_db}.{TABLE_NAME}"
    else:  # Fully qualified name provided
        fully_qualified_table = TABLE_NAME


    generate_sql = f'''

	WITH EVENT_COLUMNS as (
	SELECT 
	    f.key as column_name,
	    LISTAGG(DISTINCT (CASE WHEN TYPEOF(f.value)='NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END),', ') as data_type
	  FROM amplitude_events_raw t,
	  LATERAL FLATTEN(input => t.json_data) f
	  GROUP BY f.key
	)
	SELECT 
	'CREATE OR REPLACE TABLE {fully_qualified_table} AS  \n' ||
	'SELECT \n' ||
	LISTAGG(DISTINCT 'json_data:"' ||column_name || '"::' || data_type || ' as "' ||column_name || '"', ',\n') ||
	'\nFROM amplitude_events_raw;' as generated_sql
	FROM EVENT_COLUMNS
	WHERE (data_type NOT IN ('OBJECT','ARRAY')
	AND data_type NOT LIKE '%,%')

    '''

    # Execute the SQL to create a dataframe of the result
    df = snowpark_session.sql(generate_sql).collect()

    # Get the first row
    sql_text = df[0]['GENERATED_SQL']

    # Execute the SQL to create the table directly
    snowpark_session.sql(sql_text).collect()
    
    # Return a message indicating success
    row_count = snowpark_session.sql(f"SELECT COUNT(*) AS COUNT FROM {fully_qualified_table}").collect()[0]['COUNT']
    return f"Table {fully_qualified_table} created successfully with {row_count} rows"

$$;

CALL UPDATE_EVENTS_TABLE('events');
```

Can you create a procedure for the user_properties tables using the generated SQL from earlier. 
If time create an additional argument to take any of the nested json keys, e.g. "event_properties"

</details>

---

### Snowflake Stored Procedures

You can write stored procedures to extend the system with procedural code. With a procedure, you can use branching, looping, and other programmatic constructs. You can reuse a procedure multiple times by calling it from other code.

A Snowflake stored procedure code is wrapped in a function taking the snowpark_session and any arguments you have given as options. The snowpark_session will give you access to execute SQL queries through Python. 

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
RUNTIME_VERSION = '3.10'
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

The objects returned from a query are returned as a dataframe object

[Row(TODAY=datetime.date(2025, 5, 21))]

We can extract the exact value from the dataframe using [0] to select the first row and ['TODAY'] to select the column. Recreate the procedure selecting the value from your dataframe to verify this works.

```
CREATE OR REPLACE PROCEDURE TODAY()
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
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
RUNTIME_VERSION = '3.10'
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

For our example here of having SQL write the SQL query, we can now have a Stored Procedure that will execute the generated SQL query.

### Create Tables from the Raw Amplitude Data

Execute these calls to a stored procedure, these will provide you with SQL code to create the Silver layer of your Amplitude Data Source. 

#### To do

1. Update these procedures to call your raw events table, picked the nested json section (e.g. user_properties), and table where you want to write the data. 
2. Retreive the SQL, execute the code to confirm the tables can be built
3. Create a stored procedure for each table with the SQL code you retrieved in step 2.
4. Bonus: If you're feeling confidient try building your procedures from procedure in step 1. 


Note for groups and group_properties you may not receive any data, in which case these can be skipped. 

AMP_EVENTS
```
CALL TIL_DATA_ENGINEERING.WJSUTTON_STAGING.GENERATE_FLATTENED_JSON(
    'TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON',
    '',
    'AMP_EVENTS'
);
```
<details>
    <summary>Generated SQL</summary>
	
```
CREATE OR REPLACE TABLE AMP_EVENTS AS
SELECT
            json_data:"$insert_id"::VARCHAR AS "$insert_id",
            json_data:"client_event_time"::VARCHAR AS "client_event_time",
            json_data:"event_type"::VARCHAR AS "event_type",
            json_data:"device_manufacturer"::VARCHAR AS "device_manufacturer",
            json_data:"country"::VARCHAR AS "country",
            json_data:"server_received_time"::VARCHAR AS "server_received_time",
            json_data:"ip_address"::VARCHAR AS "ip_address",
            json_data:"amplitude_event_type"::VARCHAR AS "amplitude_event_type",
            json_data:"os_version"::VARCHAR AS "os_version",
            json_data:"version_name"::VARCHAR AS "version_name",
            json_data:"user_id"::VARCHAR AS "user_id",
            json_data:"$schema"::VARCHAR AS "$schema",
            json_data:"app"::INTEGER AS "app",
            json_data:"platform"::VARCHAR AS "platform",
            json_data:"data_type"::VARCHAR AS "data_type",
            json_data:"adid"::VARCHAR AS "adid",
            json_data:"is_attribution_event"::VARCHAR AS "is_attribution_event",
            json_data:"sample_rate"::VARCHAR AS "sample_rate",
            json_data:"source_id"::VARCHAR AS "source_id",
            json_data:"partner_id"::VARCHAR AS "partner_id",
            json_data:"device_family"::VARCHAR AS "device_family",
            json_data:"library"::VARCHAR AS "library",
            json_data:"location_lng"::VARCHAR AS "location_lng",
            json_data:"event_id"::INTEGER AS "event_id",
            json_data:"paying"::VARCHAR AS "paying",
            json_data:"os_name"::VARCHAR AS "os_name",
            json_data:"idfa"::VARCHAR AS "idfa",
            json_data:"start_version"::VARCHAR AS "start_version",
            json_data:"amplitude_id"::INTEGER AS "amplitude_id",
            json_data:"$insert_key"::VARCHAR AS "$insert_key",
            json_data:"server_upload_time"::VARCHAR AS "server_upload_time",
            json_data:"language"::VARCHAR AS "language",
            json_data:"uuid"::VARCHAR AS "uuid",
            json_data:"device_brand"::VARCHAR AS "device_brand",
            json_data:"global_user_properties"::VARCHAR AS "global_user_properties",
            json_data:"session_id"::INTEGER AS "session_id",
            json_data:"city"::VARCHAR AS "city",
            json_data:"client_upload_time"::VARCHAR AS "client_upload_time",
            json_data:"user_creation_time"::VARCHAR AS "user_creation_time",
            json_data:"device_type"::VARCHAR AS "device_type",
            json_data:"amplitude_attribution_ids"::VARCHAR AS "amplitude_attribution_ids",
            json_data:"device_id"::VARCHAR AS "device_id",
            json_data:"region"::VARCHAR AS "region",
            json_data:"device_model"::VARCHAR AS "device_model",
            json_data:"event_time"::VARCHAR AS "event_time",
            json_data:"processed_time"::VARCHAR AS "processed_time",
            json_data:"dma"::VARCHAR AS "dma",
            json_data:"device_carrier"::VARCHAR AS "device_carrier",
            json_data:"location_lat"::VARCHAR AS "location_lat"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
;
```
	
</details>

AMP_USER_PROPERTIES
```
CALL TIL_DATA_ENGINEERING.WJSUTTON_STAGING.GENERATE_FLATTENED_JSON(
    'TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON',
    'user_properties',
    'AMP_USER_PROPERTIES'
);
```

<details>
    <summary>Generated SQL</summary>
	
```
CREATE OR REPLACE TABLE AMP_USER_PROPERTIES AS
SELECT
            json_data:event_id::INT AS event_id,
            json_data:session_id::INT AS session_id,
            json_data:user_properties:"initial_fbclid"::VARCHAR AS "initial_fbclid",
            json_data:user_properties:"referrer"::VARCHAR AS "referrer",
            json_data:user_properties:"referring_domain"::VARCHAR AS "referring_domain",
            json_data:user_properties:"initial_referrer"::VARCHAR AS "initial_referrer",
            json_data:user_properties:"initial_utm_medium"::VARCHAR AS "initial_utm_medium",
            json_data:user_properties:"initial_utm_campaign"::VARCHAR AS "initial_utm_campaign",
            json_data:user_properties:"initial_utm_content"::VARCHAR AS "initial_utm_content",
            json_data:user_properties:"initial_msclkid"::VARCHAR AS "initial_msclkid",
            json_data:user_properties:"initial_referring_domain"::VARCHAR AS "initial_referring_domain",
            json_data:user_properties:"initial_gclid"::VARCHAR AS "initial_gclid",
            json_data:user_properties:"initial_ttclid"::VARCHAR AS "initial_ttclid",
            json_data:user_properties:"initial_dclid"::VARCHAR AS "initial_dclid",
            json_data:user_properties:"utm_medium"::VARCHAR AS "utm_medium",
            json_data:user_properties:"initial_twclid"::VARCHAR AS "initial_twclid",
            json_data:user_properties:"utm_campaign"::VARCHAR AS "utm_campaign",
            json_data:user_properties:"fbclid"::VARCHAR AS "fbclid",
            json_data:user_properties:"initial_ko_click_id"::VARCHAR AS "initial_ko_click_id",
            json_data:user_properties:"initial_li_fat_id"::VARCHAR AS "initial_li_fat_id",
            json_data:user_properties:"initial_utm_term"::VARCHAR AS "initial_utm_term",
            json_data:user_properties:"initial_gbraid"::VARCHAR AS "initial_gbraid",
            json_data:user_properties:"initial_utm_id"::VARCHAR AS "initial_utm_id",
            json_data:user_properties:"utm_source"::VARCHAR AS "utm_source",
            json_data:user_properties:"initial_rtd_cid"::VARCHAR AS "initial_rtd_cid",
            json_data:user_properties:"initial_wbraid"::VARCHAR AS "initial_wbraid",
            json_data:user_properties:"initial_utm_source"::VARCHAR AS "initial_utm_source"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
WHERE json_data:user_properties IS NOT NULL AND json_data:user_properties <> PARSE_JSON('{}');
```
	
</details>


AMP_EVENT_PROPERTIES
```
CALL TIL_DATA_ENGINEERING.WJSUTTON_STAGING.GENERATE_FLATTENED_JSON(
    'TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON',
    'event_properties',
    'AMP_EVENT_PROPERTIES'
);
```
<details>
    <summary>Generated SQL</summary>
	
```
CREATE OR REPLACE TABLE AMP_EVENT_PROPERTIES AS
SELECT
            json_data:event_id::INT AS event_id,
            json_data:session_id::INT AS session_id,
            json_data:event_properties:"referring_domain"::VARCHAR AS "referring_domain",
            json_data:event_properties:"referrer"::VARCHAR AS "referrer",
            json_data:event_properties:"[Amplitude] Element Selector"::VARCHAR AS "[Amplitude] Element Selector",
            json_data:event_properties:"[Amplitude] Element Tag"::VARCHAR AS "[Amplitude] Element Tag",
            json_data:event_properties:"code"::VARCHAR AS "code",
            json_data:event_properties:"[Amplitude] Element Position Top"::INTEGER AS "[Amplitude] Element Position Top",
            json_data:event_properties:"[Amplitude] Element Aria Label"::VARCHAR AS "[Amplitude] Element Aria Label",
            json_data:event_properties:"[Amplitude] Form Destination"::VARCHAR AS "[Amplitude] Form Destination",
            json_data:event_properties:"action"::VARCHAR AS "action",
            json_data:event_properties:"[Amplitude] Page Title"::VARCHAR AS "[Amplitude] Page Title",
            json_data:event_properties:"[Amplitude] Element ID"::VARCHAR AS "[Amplitude] Element ID",
            json_data:event_properties:"[Amplitude] Element Parent Label"::VARCHAR AS "[Amplitude] Element Parent Label",
            json_data:event_properties:"[Amplitude] Page URL"::VARCHAR AS "[Amplitude] Page URL",
            json_data:event_properties:"video_progress"::DECIMAL AS "video_progress",
            json_data:event_properties:"video_url"::VARCHAR AS "video_url",
            json_data:event_properties:"[Amplitude] Page Counter"::INTEGER AS "[Amplitude] Page Counter",
            json_data:event_properties:"video"::VARCHAR AS "video",
            json_data:event_properties:"[Amplitude] Session Replay ID"::VARCHAR AS "[Amplitude] Session Replay ID",
            json_data:event_properties:"utm_medium"::VARCHAR AS "utm_medium",
            json_data:event_properties:"utm_campaign"::VARCHAR AS "utm_campaign",
            json_data:event_properties:"fbclid"::VARCHAR AS "fbclid",
            json_data:event_properties:"playlist"::VARCHAR AS "playlist",
            json_data:event_properties:"[Amplitude] Page Path"::VARCHAR AS "[Amplitude] Page Path",
            json_data:event_properties:"video_watchTime"::DECIMAL AS "video_watchTime",
            json_data:event_properties:"[Amplitude] Element Position Left"::INTEGER AS "[Amplitude] Element Position Left",
            json_data:event_properties:"[Amplitude] Element Href"::VARCHAR AS "[Amplitude] Element Href",
            json_data:event_properties:"[Amplitude] Page Domain"::VARCHAR AS "[Amplitude] Page Domain",
            json_data:event_properties:"[Amplitude] Element Text"::VARCHAR AS "[Amplitude] Element Text",
            json_data:event_properties:"utm_source"::VARCHAR AS "utm_source",
            json_data:event_properties:"[Amplitude] Viewport Width"::INTEGER AS "[Amplitude] Viewport Width",
            json_data:event_properties:"[Amplitude] Element Class"::VARCHAR AS "[Amplitude] Element Class",
            json_data:event_properties:"[Amplitude] Page Location"::VARCHAR AS "[Amplitude] Page Location",
            json_data:event_properties:"[Amplitude] Viewport Height"::INTEGER AS "[Amplitude] Viewport Height"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
WHERE json_data:event_properties IS NOT NULL AND json_data:event_properties <> PARSE_JSON('{}');
```
	
</details>


AMP_GROUPS
```
CALL TIL_DATA_ENGINEERING.WJSUTTON_STAGING.GENERATE_FLATTENED_JSON(
    'TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON',
    'groups',
    'AMP_GROUPS'
);
```
<details>
    <summary>Generated SQL</summary>
	
```
No flattenable columns found for the given JSON path, or the path does not exist/contains only objects/arrays.
```
</details>

AMP_GROUP_PROPERTIES
```
CALL TIL_DATA_ENGINEERING.WJSUTTON_STAGING.GENERATE_FLATTENED_JSON(
    'TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON',
    'group_properties',
    'AMP_GROUP_PROPERTIES'
);
```
<details>
    <summary>Generated SQL</summary>
	
```
No flattenable columns found for the given JSON path, or the path does not exist/contains only objects/arrays.
```
</details>

AMP_DATA
```
CALL TIL_DATA_ENGINEERING.WJSUTTON_STAGING.GENERATE_FLATTENED_JSON(
    'TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON',
    'data',
    'AMP_DATA'
);
```
<details>
    <summary>Generated SQL</summary>

```
CREATE OR REPLACE TABLE AMP_DATA AS
SELECT
            json_data:event_id::INT AS event_id,
            json_data:session_id::INT AS session_id,
            json_data:data:"path"::VARCHAR AS "path",
            json_data:data:"user_properties_updated"::BOOLEAN AS "user_properties_updated"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
WHERE json_data:data IS NOT NULL AND json_data:data <> PARSE_JSON('{}');
```

</details>

<details>
    <summary>Example Stored Procedure for AMP_DATA Table Creation as SQL</summary>

Note: the query is wrapped in a single quote <b>'</b> so you will need to:
- end the string with a single quote before the semi-colon (;)
- double single quote any quotes as part of the query
- e.g. PARSE_JSON('{}') needs to be PARSE_JSON(''{}'') here 

```
CREATE OR REPLACE PROCEDURE CREATE_AMP_DATA(TABLE_NAME STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
BEGIN
    LET sql_query STRING := 'CREATE OR REPLACE TABLE ' || TABLE_NAME || ' AS
    SELECT
        json_data:event_id::INT AS event_id,
        json_data:session_id::INT AS session_id,
        json_data:data:"path"::VARCHAR AS "path",
        json_data:data:"user_properties_updated"::BOOLEAN AS "user_properties_updated"
    FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
    WHERE json_data:data IS NOT NULL AND json_data:data <> PARSE_JSON(''{}'')';
    
    EXECUTE IMMEDIATE sql_query;
    
    RETURN 'Table ' || TABLE_NAME || ' created successfully';
END;
$$;
```

</details>

### Automating this for new data arrival

If you haven't please configure a SNOWPIPE to move data from your stage to the raw table as described at the end of last week's session: [Week 2 Amplitude: auto-ingest-data-with-snowpipe](https://github.com/TheInformationLab/data_engineering_school_course/blob/des3-updates/course_docs/week_2_amplitude_load.md#auto-ingest-data-with-snowpipe) 

This will mean any new data flows into your raw table, now we need to move the data into the silver layer. To do this we will need to configure a `STREAM` and `TASKS`.

#### Step 1: Create a Stream on Your Source Table

A stream tracks real-time data changes (inserts/updates/deletes). Create one for your source table:

```
CREATE STREAM amplitude_source_stream ON TABLE AMPLITUDE_EVENTS_RAW_PYTHON;
```

#### Step 2: Consolidate Stored Procedures
Since tasks execute only one SQL statement or stored procedure we will need to create a Stored Procedure of the previous procedures. 

```
CREATE OR REPLACE PROCEDURE run_amp_silver_layer()  
RETURNS STRING  
LANGUAGE SQL  
AS  
$$  
  BEGIN  
    CALL CREATE_AMP_EVENTS(AMP_EVENTS);
    CALL CREATE_AMP_USER_PROPERTIES(AMP_USER_PROPERTIES);
    CALL CREATE_AMP_EVENT_PROPERTIES(AMP_EVENT_PROPERTIES);  
    CALL CREATE_AMP_DATA(AMP_DATA);  
    RETURN 'Silver layer rebuilt';  
  END;  
$$;  

```
#### Step 3: Create a Conditional Task

Schedule a task that runs only when the stream contains new data:
```
CREATE TASK amp_silver_layer_trigger  
WAREHOUSE = DATASCHOOL_WH
SCHEDULE = '5 MINUTE' 
WHEN SYSTEM$STREAM_HAS_DATA('amplitude_source_stream')  
AS  
  CALL run_amp_silver_layer();
```

#### Step 4: Activate the Task

```
ALTER TASK amp_silver_layer_trigger RESUME;
```

#### Step 5: Monitor the Task

Upload some new data your to S3 Bucket, this shoudl trigger SNOWPIPE to move the data to your raw tables then this task should start shortly afterwards. 
```
SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY());  
```

</details>

<details>
    <summary>Solution</summary>
	
```
CREATE OR REPLACE PROCEDURE CREATE_AMP_EVENTS(TABLE_NAME STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
BEGIN
    LET sql_query STRING := 'CREATE OR REPLACE TABLE ' || TABLE_NAME || ' AS
    SELECT
            json_data:"$insert_id"::VARCHAR AS "$insert_id",
            json_data:"client_event_time"::VARCHAR AS "client_event_time",
            json_data:"event_type"::VARCHAR AS "event_type",
            json_data:"device_manufacturer"::VARCHAR AS "device_manufacturer",
            json_data:"country"::VARCHAR AS "country",
            json_data:"server_received_time"::VARCHAR AS "server_received_time",
            json_data:"ip_address"::VARCHAR AS "ip_address",
            json_data:"amplitude_event_type"::VARCHAR AS "amplitude_event_type",
            json_data:"os_version"::VARCHAR AS "os_version",
            json_data:"version_name"::VARCHAR AS "version_name",
            json_data:"user_id"::VARCHAR AS "user_id",
            json_data:"$schema"::VARCHAR AS "$schema",
            json_data:"app"::INTEGER AS "app",
            json_data:"platform"::VARCHAR AS "platform",
            json_data:"data_type"::VARCHAR AS "data_type",
            json_data:"adid"::VARCHAR AS "adid",
            json_data:"is_attribution_event"::VARCHAR AS "is_attribution_event",
            json_data:"sample_rate"::VARCHAR AS "sample_rate",
            json_data:"source_id"::VARCHAR AS "source_id",
            json_data:"partner_id"::VARCHAR AS "partner_id",
            json_data:"device_family"::VARCHAR AS "device_family",
            json_data:"library"::VARCHAR AS "library",
            json_data:"location_lng"::VARCHAR AS "location_lng",
            json_data:"event_id"::INTEGER AS "event_id",
            json_data:"paying"::VARCHAR AS "paying",
            json_data:"os_name"::VARCHAR AS "os_name",
            json_data:"idfa"::VARCHAR AS "idfa",
            json_data:"start_version"::VARCHAR AS "start_version",
            json_data:"amplitude_id"::INTEGER AS "amplitude_id",
            json_data:"$insert_key"::VARCHAR AS "$insert_key",
            json_data:"server_upload_time"::VARCHAR AS "server_upload_time",
            json_data:"language"::VARCHAR AS "language",
            json_data:"uuid"::VARCHAR AS "uuid",
            json_data:"device_brand"::VARCHAR AS "device_brand",
            json_data:"global_user_properties"::VARCHAR AS "global_user_properties",
            json_data:"session_id"::INTEGER AS "session_id",
            json_data:"city"::VARCHAR AS "city",
            json_data:"client_upload_time"::VARCHAR AS "client_upload_time",
            json_data:"user_creation_time"::VARCHAR AS "user_creation_time",
            json_data:"device_type"::VARCHAR AS "device_type",
            json_data:"amplitude_attribution_ids"::VARCHAR AS "amplitude_attribution_ids",
            json_data:"device_id"::VARCHAR AS "device_id",
            json_data:"region"::VARCHAR AS "region",
            json_data:"device_model"::VARCHAR AS "device_model",
            json_data:"event_time"::VARCHAR AS "event_time",
            json_data:"processed_time"::VARCHAR AS "processed_time",
            json_data:"dma"::VARCHAR AS "dma",
            json_data:"device_carrier"::VARCHAR AS "device_carrier",
            json_data:"location_lat"::VARCHAR AS "location_lat"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
';
    
    EXECUTE IMMEDIATE sql_query;
    
    RETURN 'Table ' || TABLE_NAME || ' created successfully';
END;
$$;

CREATE OR REPLACE PROCEDURE CREATE_AMP_USER_PROPERTIES(TABLE_NAME STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
BEGIN
    LET sql_query STRING := 'CREATE OR REPLACE TABLE ' || TABLE_NAME || ' AS
    SELECT
            json_data:event_id::INT AS event_id,
            json_data:session_id::INT AS session_id,
            json_data:user_properties:"initial_fbclid"::VARCHAR AS "initial_fbclid",
            json_data:user_properties:"referrer"::VARCHAR AS "referrer",
            json_data:user_properties:"referring_domain"::VARCHAR AS "referring_domain",
            json_data:user_properties:"initial_referrer"::VARCHAR AS "initial_referrer",
            json_data:user_properties:"initial_utm_medium"::VARCHAR AS "initial_utm_medium",
            json_data:user_properties:"initial_utm_campaign"::VARCHAR AS "initial_utm_campaign",
            json_data:user_properties:"initial_utm_content"::VARCHAR AS "initial_utm_content",
            json_data:user_properties:"initial_msclkid"::VARCHAR AS "initial_msclkid",
            json_data:user_properties:"initial_referring_domain"::VARCHAR AS "initial_referring_domain",
            json_data:user_properties:"initial_gclid"::VARCHAR AS "initial_gclid",
            json_data:user_properties:"initial_ttclid"::VARCHAR AS "initial_ttclid",
            json_data:user_properties:"initial_dclid"::VARCHAR AS "initial_dclid",
            json_data:user_properties:"utm_medium"::VARCHAR AS "utm_medium",
            json_data:user_properties:"initial_twclid"::VARCHAR AS "initial_twclid",
            json_data:user_properties:"utm_campaign"::VARCHAR AS "utm_campaign",
            json_data:user_properties:"fbclid"::VARCHAR AS "fbclid",
            json_data:user_properties:"initial_ko_click_id"::VARCHAR AS "initial_ko_click_id",
            json_data:user_properties:"initial_li_fat_id"::VARCHAR AS "initial_li_fat_id",
            json_data:user_properties:"initial_utm_term"::VARCHAR AS "initial_utm_term",
            json_data:user_properties:"initial_gbraid"::VARCHAR AS "initial_gbraid",
            json_data:user_properties:"initial_utm_id"::VARCHAR AS "initial_utm_id",
            json_data:user_properties:"utm_source"::VARCHAR AS "utm_source",
            json_data:user_properties:"initial_rtd_cid"::VARCHAR AS "initial_rtd_cid",
            json_data:user_properties:"initial_wbraid"::VARCHAR AS "initial_wbraid",
            json_data:user_properties:"initial_utm_source"::VARCHAR AS "initial_utm_source"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
WHERE json_data:user_properties IS NOT NULL AND json_data:user_properties <> PARSE_JSON(''{}'')';
    
    EXECUTE IMMEDIATE sql_query;
    
    RETURN 'Table ' || TABLE_NAME || ' created successfully';
END;
$$;

CREATE OR REPLACE PROCEDURE CREATE_AMP_EVENT_PROPERTIES(TABLE_NAME STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
BEGIN
    LET sql_query STRING := 'CREATE OR REPLACE TABLE ' || TABLE_NAME || ' AS
    SELECT
            json_data:event_id::INT AS event_id,
            json_data:session_id::INT AS session_id,
            json_data:event_properties:"referring_domain"::VARCHAR AS "referring_domain",
            json_data:event_properties:"referrer"::VARCHAR AS "referrer",
            json_data:event_properties:"[Amplitude] Element Selector"::VARCHAR AS "[Amplitude] Element Selector",
            json_data:event_properties:"[Amplitude] Element Tag"::VARCHAR AS "[Amplitude] Element Tag",
            json_data:event_properties:"code"::VARCHAR AS "code",
            json_data:event_properties:"[Amplitude] Element Position Top"::INTEGER AS "[Amplitude] Element Position Top",
            json_data:event_properties:"[Amplitude] Element Aria Label"::VARCHAR AS "[Amplitude] Element Aria Label",
            json_data:event_properties:"[Amplitude] Form Destination"::VARCHAR AS "[Amplitude] Form Destination",
            json_data:event_properties:"action"::VARCHAR AS "action",
            json_data:event_properties:"[Amplitude] Page Title"::VARCHAR AS "[Amplitude] Page Title",
            json_data:event_properties:"[Amplitude] Element ID"::VARCHAR AS "[Amplitude] Element ID",
            json_data:event_properties:"[Amplitude] Element Parent Label"::VARCHAR AS "[Amplitude] Element Parent Label",
            json_data:event_properties:"[Amplitude] Page URL"::VARCHAR AS "[Amplitude] Page URL",
            json_data:event_properties:"video_progress"::DECIMAL AS "video_progress",
            json_data:event_properties:"video_url"::VARCHAR AS "video_url",
            json_data:event_properties:"[Amplitude] Page Counter"::INTEGER AS "[Amplitude] Page Counter",
            json_data:event_properties:"video"::VARCHAR AS "video",
            json_data:event_properties:"[Amplitude] Session Replay ID"::VARCHAR AS "[Amplitude] Session Replay ID",
            json_data:event_properties:"utm_medium"::VARCHAR AS "utm_medium",
            json_data:event_properties:"utm_campaign"::VARCHAR AS "utm_campaign",
            json_data:event_properties:"fbclid"::VARCHAR AS "fbclid",
            json_data:event_properties:"playlist"::VARCHAR AS "playlist",
            json_data:event_properties:"[Amplitude] Page Path"::VARCHAR AS "[Amplitude] Page Path",
            json_data:event_properties:"video_watchTime"::DECIMAL AS "video_watchTime",
            json_data:event_properties:"[Amplitude] Element Position Left"::INTEGER AS "[Amplitude] Element Position Left",
            json_data:event_properties:"[Amplitude] Element Href"::VARCHAR AS "[Amplitude] Element Href",
            json_data:event_properties:"[Amplitude] Page Domain"::VARCHAR AS "[Amplitude] Page Domain",
            json_data:event_properties:"[Amplitude] Element Text"::VARCHAR AS "[Amplitude] Element Text",
            json_data:event_properties:"utm_source"::VARCHAR AS "utm_source",
            json_data:event_properties:"[Amplitude] Viewport Width"::INTEGER AS "[Amplitude] Viewport Width",
            json_data:event_properties:"[Amplitude] Element Class"::VARCHAR AS "[Amplitude] Element Class",
            json_data:event_properties:"[Amplitude] Page Location"::VARCHAR AS "[Amplitude] Page Location",
            json_data:event_properties:"[Amplitude] Viewport Height"::INTEGER AS "[Amplitude] Viewport Height"
FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
WHERE json_data:event_properties IS NOT NULL AND json_data:event_properties <> PARSE_JSON(''{}'')';
    
    EXECUTE IMMEDIATE sql_query;
    
    RETURN 'Table ' || TABLE_NAME || ' created successfully';
END;
$$;


CREATE OR REPLACE PROCEDURE CREATE_AMP_DATA(TABLE_NAME STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
BEGIN
    LET sql_query STRING := 'CREATE OR REPLACE TABLE ' || TABLE_NAME || ' AS
    SELECT
        json_data:event_id::INT AS event_id,
        json_data:session_id::INT AS session_id,
        json_data:data:"path"::VARCHAR AS "path",
        json_data:data:"user_properties_updated"::BOOLEAN AS "user_properties_updated"
    FROM TIL_DATA_ENGINEERING.WJSUTTON_STAGING.AMPLITUDE_EVENTS_RAW_PYTHON
    WHERE json_data:data IS NOT NULL AND json_data:data <> PARSE_JSON(''{}'')';
    
    EXECUTE IMMEDIATE sql_query;
    
    RETURN 'Table ' || TABLE_NAME || ' created successfully';
END;
$$;

CREATE OR REPLACE STREAM amplitude_source_stream ON TABLE AMPLITUDE_EVENTS_RAW_PYTHON;

CREATE OR REPLACE PROCEDURE run_amp_silver_layer()  
RETURNS STRING  
LANGUAGE SQL  
AS  
$$  
  BEGIN  
    CALL CREATE_AMP_EVENTS(AMP_EVENTS);
    CALL CREATE_AMP_USER_PROPERTIES(AMP_USER_PROPERTIES);
    CALL CREATE_AMP_EVENT_PROPERTIES(AMP_EVENT_PROPERTIES);  
    CALL CREATE_AMP_DATA(AMP_DATA);  
    RETURN 'Silver layer rebuilt';  
  END;  
$$;  

CREATE TASK amp_silver_layer_trigger  
WAREHOUSE = DATASCHOOL_WH
SCHEDULE = '5 MINUTE' 
WHEN SYSTEM$STREAM_HAS_DATA('amplitude_source_stream')  
AS  
  CALL run_amp_silver_layer();

ALTER TASK amp_silver_layer_trigger RESUME;

SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE name = 'AMP_SILVER_LAYER_TRIGGER';

-- Import new data into the stage and rerun the step above
        
```
</details>

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