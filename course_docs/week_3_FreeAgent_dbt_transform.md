
# Transform Project: FreeAgent in dbt
### Week 3 | Friday | Instructor Led Walkthrough

## Learning Objectives

- Migrating SQL to dbt

### dbt Studio

dbt Studio is the main development interface on dbt Platform, it lets you edit models, see lineage and execute dbt build. 

- Create Branch: `<your-name>-staging-data`

### Migration

You are to migrate the Silver layer you built in Monday's FreeAgent session from Snowflake to dbt.

Requirements:
- All dbt project code should be on GitHub 
- The merge/insert logic you used in your stored procedures is to be replicated using materialisation logic in dbt. This ensures visibility of the data lineage
- Complete [dbt's Onboarding Exit Criteria](../course_docs/dbt_onboarding_exit_criteria.md) including the recommendations



#### Starter Walkthroughs and Resources


<details>
    <summary>Migrating Tables to dbt</summary>

### Migrating Tables to dbt

Create a scratch pad and write “select * from your_schema.a_table” and hit preview.

```
SELECT *
FROM <your-name>_freeagent_STAGING.STG_CONTACTS
```

Make a new folder in models called `staging`, and with that, another folder called `freeagent` and delete the model `example`

Configure dbt_project.yml to reference your new model.

```
models:
  my_new_project:
    staging:
      freeagent:
        +materialized: table
```

Define a schema.yml file with your source tables.

```
version: 2

sources:
  - name: <source_name>
    database: <database_name>
    schema: <schema_name>
    tables:
      - name: <table_name>
      - ...

```

When you have entered details of a table, click 'Generate Model'. This will autopopulate a dbt model in a staging format of the data. 

Our Bronze tables only have one column, `raw_data`, so the generated model will just select that column. It gives you the file and the `{{ source() }}` reference to start from; you'll replace the SELECT with the flattening logic from your stored procedures (see Creating Models in dbt below).

Save this in your `freeagent` folder if it is not already there. Repeat this step for the other staging tables in your Snowflake schema.

A note on naming: our Bronze tables in Snowflake are already called `stg_contacts`, `stg_users` etc. dbt's convention is to name staging models `stg_<source>__<table>`, e.g. `stg_freeagent__contacts`, which keeps them distinct from the tables they read from.

Add these staging models to your schema.yml file below the sources block.

```
models:
  - name: stg_freeagent__contacts
  - name: <model name>

```

Do `dbt run --select staging.freeagent` to run everything in the freeagent model folder.

</details>

<details>
    <summary>Creating Models in dbt</summary>

As we have the raw SQL for our table creation we can migrate the Stored Procedure to dbt. 

For this we will need to reference the source table `stg_contacts` in our Silver layer. 

Example for DIM_CONTACTS
In SQL:
```
CREATE OR REPLACE TABLE DIM_CONTACTS AS
SELECT
    CAST(REGEXP_SUBSTR(c.value:url::STRING, '/contacts/([0-9]+)$', 1, 1, 'e') AS INT) AS contact_id,
    c.value:organisation_name::STRING AS organisation_name,
    c.value:first_name::STRING AS first_name,
    c.value:last_name::STRING AS last_name,
    c.value:email::STRING AS email,
    c.value:status::STRING AS status,
    c.value:updated_at::TIMESTAMP_TZ AS updated_at
FROM TIL_DATA_ENGINEERING.<your-name>_freeagent_STAGING.STG_CONTACTS,
LATERAL FLATTEN(input => raw_data:contacts) c
QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY updated_at DESC) = 1;
```
In dbt:

stg_freeagent__contacts.sql
```
SELECT
    CAST(REGEXP_SUBSTR(c.value:url::STRING, '/contacts/([0-9]+)$', 1, 1, 'e') AS INT) AS contact_id,
    c.value:organisation_name::STRING AS organisation_name,
    c.value:first_name::STRING AS first_name,
    c.value:last_name::STRING AS last_name,
    c.value:email::STRING AS email,
    c.value:status::STRING AS status,
    c.value:updated_at::TIMESTAMP_TZ AS updated_at
FROM {{ source('freeagent', 'stg_contacts') }},
LATERAL FLATTEN(input => raw_data:contacts) c
QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY updated_at DESC) = 1
```
We have:
- removed the `CREATE OR REPLACE TABLE` line, dbt creates the table for us from the materialisation in dbt_project.yml
- updated the FROM to not be a hard-coded table name but our source table from the schema.yml
- removed the trailing semi-colon, dbt wraps the model in its own SQL so a `;` will cause an error

Models that join to another model should use `{{ ref('stg_freeagent__contacts') }}` rather than the table name, this is how dbt builds the lineage graph and runs models in the right order.


Update the schema.yml with all of the models from the silver layer:

schema.yml
```
version: 2

sources:
  - name: freeagent
    database: til_data_engineering
    schema: <your-name>_freeagent_staging
    tables:
      - name: stg_contacts
      - name: stg_users
      - name: stg_projects
      - name: stg_invoices
      - name: stg_timeslips

models:
  - name: stg_freeagent__contacts
    columns:
      - name: contact_id
        data_tests:
          - unique
          - not_null
  - name: stg_freeagent__users
  - name: stg_freeagent__projects
  - name: stg_freeagent__invoices
  - name: stg_freeagent__timeslips

```

</details>


<details>
    <summary>Incremental models (replacing MERGE / INSERT)</summary>

A model materialised as a `table` is rebuilt from scratch every run, the same as the `CREATE OR REPLACE TABLE` procedures. To replicate the MERGE logic from your stored procedures, use the `incremental` materialisation.

- On the first run (or with `dbt build --full-refresh`) dbt builds the whole table.
- On later runs, the `{% if is_incremental() %}` block is added, so only new rows are selected.
- `unique_key` tells dbt to MERGE: rows that match an existing key are updated, the rest are inserted. Without a `unique_key` dbt simply INSERTs.

stg_freeagent__contacts.sql
```
{{ config(
    materialized='incremental',
    unique_key='contact_id'
) }}

WITH contacts AS (
    SELECT
        CAST(REGEXP_SUBSTR(c.value:url::STRING, '/contacts/([0-9]+)$', 1, 1, 'e') AS INT) AS contact_id,
        c.value:organisation_name::STRING AS organisation_name,
        c.value:first_name::STRING AS first_name,
        c.value:last_name::STRING AS last_name,
        c.value:email::STRING AS email,
        c.value:status::STRING AS status,
        c.value:updated_at::TIMESTAMP_TZ AS updated_at
    FROM {{ source('freeagent', 'stg_contacts') }},
    LATERAL FLATTEN(input => raw_data:contacts) c
)

SELECT *
FROM contacts
{% if is_incremental() %}
-- only records changed since the last run; {{ this }} is the existing table
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY updated_at DESC) = 1
```

The `QUALIFY` is still needed: each extract run lands a new file in Bronze, so the same contact can appear more than once in a single run.

</details>


<details>
    <summary>Adding tests to dbt</summary>

It is recommended to always add the standard tests for unique & not_null, which can be applied in the models section of your schema.yml file. For example

```
models:
  - name: stg_freeagent__contacts
    columns:
      - name: contact_id
        data_tests:
          - unique
          - not_null
```

The `relationships` test checks a foreign key, e.g. every project belongs to a contact that exists:

```
  - name: stg_freeagent__projects
    columns:
      - name: contact_id
        data_tests:
          - relationships:
              to: ref('stg_freeagent__contacts')
              field: contact_id
```

Do `dbt build --select staging.freeagent` to create everything in the freeagent model folder and run the tests defined against the models.

</details>

<details>
    <summary>Schedule a Refresh in dbt Platform (cloud)</summary>

#### Schedule a Refresh of Silver layer in dbt Platform (cloud)

- Navigate to your project and click on the Jobs tab.
- Click Create Job (or select an existing job to edit).
- In the job settings: Under Commands, enter the command for your refresh. 

```
dbt build --select your_model_name
```

Schedule the job to run and verify it has successfully built. 
</details>


<details>
    <summary>Adding Keys to Tables from the dbt_utils package</summary>

From the dbt_utils package...

[generate_surrogate_key (source)](https://github.com/dbt-labs/dbt-utils/tree/1.3.0/?tab=readme-ov-file#generate_surrogate_key-source)

This macro implements a cross-database way to generate a hashed surrogate key using the fields specified.

**Usage:**
```
{{ dbt_utils.generate_surrogate_key(['field_a', 'field_b'[,...]]) }}
```

Create a packages.yml and insert the text to install the dbt_utils package.
```
packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.0
```

If it doesn't automatically install, run `dbt deps` to install the package. 

FreeAgent records already have a natural ID in their `url`, so most of your models won't need this. Add this macro to models where a single key is not present, for example a model of hours logged per user per day:

```
...
select
    {{ dbt_utils.generate_surrogate_key(['user_id', 'dated_on']) }} as user_day_id,
    user_id,
    dated_on,
    sum(hours) as total_hours
...
```
</details>

<details>
    <summary>Python models</summary>

#### Python models

If you built the `GENERATE_FLATTENED_TABLE` stored procedure in the stretch section, it is written in Python, and dbt can run Python models, so we can move the existing transformation logic from Snowflake to dbt. 

The majority of the existing code will work, we need to make some changes for the way dbt handles Python models.

Each Python model lives in a .py file in your models/ folder. It defines a function named model(), which takes two parameters:

**def model(dbt, session):**

- dbt: allows you to run dbt-type functions, like dbt.ref, or dbt.source
- session: allows you to reference functions from the connected database, e.g. session.sql('SELECT * FROM table;')

The model() function must return a single DataFrame.

Create `gen_freeagent__contacts.py`

```
def model(dbt, session):
    """
    dbt Python model for generating the FreeAgent contacts table
    
    This model flattens the contacts array from the FreeAgent staging table,
    extracts all non nested json columns.
    
    Args:
        dbt: The dbt context object for referencing other models
        session: The Snowpark session for executing SQL
        
    Returns:
        Snowpark DataFrame containing the flattened contacts data
    """
    dbt.config(materialized="table")

    # Reference your source table using dbt.source() 
    stg_contacts = dbt.source("freeagent", "stg_contacts")
    
    # Create temp view of the raw contacts for SQL operations
    stg_contacts.create_or_replace_temp_view("stg_contacts")

    # One row per record in the contacts array
    from_sql = "stg_contacts t, LATERAL FLATTEN(input => t.raw_data:contacts) r"

    # Code from the earlier stored procedure without the create table step
    get_columns_sql = f'''
        SELECT
            f.key AS column_name,
            LISTAGG(DISTINCT CASE WHEN TYPEOF(f.value) = 'NULL_VALUE' THEN 'VARCHAR' ELSE TYPEOF(f.value) END, ', ') AS data_type
        FROM {from_sql},
        LATERAL FLATTEN(input => r.value) f
        GROUP BY f.key
        HAVING data_type NOT IN ('OBJECT', 'ARRAY') AND data_type NOT LIKE '%,%'
    '''

    # Execute the SQL to find the columns and their data types
    columns = session.sql(get_columns_sql).collect()

    select_cols = [
        f'r.value:"{row["COLUMN_NAME"]}"::{row["DATA_TYPE"]} AS "{row["COLUMN_NAME"]}"'
        for row in columns
    ]

    # Build the SELECT statement and run it
    sql_text = "SELECT\n    " + ",\n    ".join(select_cols) + f"\nFROM {from_sql}"
    final_df = session.sql(sql_text)
    
    # Return the DataFrame - dbt will materialise this as a table
    return final_df
```

Now that we have migrated the procedure to a Python model, we can change our model references in the `schema.yml` file.

</details>


<details>
    <summary>Hooks</summary>

# Don't use this to migrate stored procedures unless you're really struggling

#### Hooks

Earlier, you created models, models always have to output data in a table-like format, e.g. SELECT * FROM table. If you wanted to run 
`DROP table`, this doesn't result in a table of data. A hook can be used to run these types of queries.

Hooks in dbt are SQL statements or snippets that run automatically at specific points during the dbt execution lifecycle. They allow you to execute custom SQL or logic before or after a model runs, helping automate tasks like setting permissions, managing metadata, or calling stored procedures.

Types of Hooks:

- **pre-hook** Runs before a model, seed, or snapshot is built. Useful for setup tasks like cleaning temporary tables or validating data.
- **post-hook** Runs after a model, seed, or snapshot is built. Commonly used to grant permissions or update metadata.
- **on-run-start** and **on-run-end** Run once at the start or end of a dbt run, useful for global setup or cleanup tasks.

Hooks can be run in three places.

1. The dbt_project.yml
```
models:
  <project_name>:
    +pre-hook:
      - "{{ some_macro() }}"
```

2. A schema.yml
```
models:
  - name: <model_name>
    config:
      pre_hook:
        - "{{ some_macro() }}"
```

3. A config block of a model
```
{{ config(
    post_hook=[
      "alter table {{ this }} ..."
    ]
) }}
SELECT * ...
```

To migrate our stored procedures, please create a macro to run them and then add it to the dbt_project.yml as a pre-hook.

Create macro `update_staging_tables.sql`, with a CALL for each of the procedures you built on Monday, e.g.

```
{% macro update_staging_tables() %}
    {% do run_query("CALL <your-name>_freeagent_STAGING.REFRESH_DIM_CONTACTS();")%}
    {% do run_query("CALL <your-name>_freeagent_STAGING.REFRESH_DIM_USERS();")%}
    {% do run_query("CALL <your-name>_freeagent_STAGING.REFRESH_DIM_PROJECTS();")%}
    {% do run_query("CALL <your-name>_freeagent_STAGING.REFRESH_FACT_INVOICES();")%}
    {% do run_query("CALL <your-name>_freeagent_STAGING.REFRESH_FACT_TIMESLIPS();")%}
{% endmacro %}
```

Update `dbt_project.yml`

```
models:
  my_new_project:
    staging:
      freeagent:
        +materialized: table
        +pre-hook:
          - "{{ update_staging_tables() }}"
```

Note that saving the stored procedure as a macro means you can run it in multiple places and only update it once.

Another note, if your procedure takes the table name as an argument (like `GENERATE_FLATTENED_TABLE`) and you remove the database and schema path from it, it will write the table to your dbt target schema. 

```
{% macro update_staging_tables() %}
    {% do run_query("CALL <your-name>_freeagent_STAGING.GENERATE_FLATTENED_TABLE('TIL_DATA_ENGINEERING.<your-name>_freeagent_STAGING.STG_CONTACTS', 'contacts', 'GEN_CONTACTS');")%}
{% endmacro %}
```

</details>


## Appendix

### References
dbt Package Hub - https://hub.getdbt.com/

dbt Incremental Models - https://docs.getdbt.com/docs/build/incremental-models

<details>
<summary>Archive</summary>

## dbt Platform Setup

### Create a Project 

Create a default project if one doesn't exist. Ensure it has a repository attached to it. 

### Create an Environment

In dbt Platform, 
- Go to the left menu and select Deploy > Environments.
- Click Create Environment.

Choose the environment type
- **Development** For interactive development in the Cloud IDE.
- **Deployment** For running scheduled jobs (choose "Production", "Staging", or "General" as needed).

- Click Development

### Set Up Database Connection
In the environment setup, you’ll see a section to configure your database connection.

Enter the required fields for your data warehouse (these will vary by database type, e.g., Snowflake, BigQuery, Databricks, Redshift, etc.):

Click Snowflake and enter details for the following:
- Account
- Database
- Warehouse
- Role

Save the connection and navigate to "Your profile" > "Credentials"

Edit the connection details for Snowflake
- Account
- Database
- Warehouse
- Role

Development Credentials
- Auth method: Username and password
- Username: From DS Snowflake Project
- Password: From DS Snowflake Project
- Schema: dbt_your_name

Test the connection and save your details.

In Settings navigate to "Your profile" > "Personal Profile"
- Link your GitHub account

In Settings navigate to "Your profile" > "CLI"
- Install the CLI (you need to remove any instance of dbt core on your machine)
- Download the CLI config and save it in C:\Users\<UserName>\.dbt (create the folder if it doesn't already exist)

### dbt CLI 

The dbt CLI will allow you to create and build models in dbt Platform (cloud) from VS Code.Your code will be synced to dbt Platform using GitHub, and dbt commands like `dbt build` will be executed in the Cloud using dbt Platform's resources. 

In VS Code:
- Sync the GitHub repo running your dbt project
- Modify the dbt_project.yml to include the dbt Platform project_id, as per "dbt Platform" > "Settings" > "Your profile" > "CLI"
- execute dbt compile to verify the CLI works
</details>
