# build_warehouse.py - Transforms raw JSON into a DuckDB Star Schema

import duckdb

con = duckdb.connect("warehouse.duckdb")

print("Initializing DuckDB warehouse build...")

# -----------------------------------------------------------------------------
# 1. STAGING LAYER: Ingest raw JSON as JSON arrays to handle optional fields
# -----------------------------------------------------------------------------
print("\n--- Phase 1: Ingesting Raw JSON to Staging ---")

con.execute("""
    CREATE OR REPLACE TABLE stg_contacts AS 
    SELECT unnest(contacts) AS c 
    FROM read_json('data/raw_contacts.json', columns={contacts: 'JSON[]'});

    CREATE OR REPLACE TABLE stg_users AS 
    SELECT unnest(users) AS u 
    FROM read_json('data/raw_users.json', columns={users: 'JSON[]'});

    CREATE OR REPLACE TABLE stg_projects AS 
    SELECT unnest(projects) AS p 
    FROM read_json('data/raw_projects.json', columns={projects: 'JSON[]'});

    CREATE OR REPLACE TABLE stg_invoices AS 
    SELECT unnest(invoices) AS inv 
    FROM read_json('data/raw_invoices.json', columns={invoices: 'JSON[]'});

    CREATE OR REPLACE TABLE stg_timeslips AS 
    SELECT unnest(timeslips) AS t 
    FROM read_json('data/raw_timeslips.json', columns={timeslips: 'JSON[]'});
""")

print("Staging tables populated successfully.")

# -----------------------------------------------------------------------------
# 2. DIMENSION TABLES: Extract integer primary keys from URI strings
# -----------------------------------------------------------------------------
print("\n--- Phase 2: Building Dimension Tables ---")

# Dim Contacts
con.execute("""
    CREATE OR REPLACE TABLE dim_contacts AS
    SELECT
        CAST(regexp_extract(c->>'$.url', '/contacts/([0-9]+)$', 1) AS INTEGER) AS contact_id,
        c->>'$.organisation_name' AS organisation_name,
        c->>'$.first_name' AS first_name,
        c->>'$.last_name' AS last_name,
        c->>'$.email' AS email,
        c->>'$.status' AS status,
        c->>'$.url' AS contact_url
    FROM stg_contacts;
""")

# Dim Users
con.execute("""
    CREATE OR REPLACE TABLE dim_users AS
    SELECT
        CAST(regexp_extract(u->>'$.url', '/users/([0-9]+)$', 1) AS INTEGER) AS user_id,
        u->>'$.first_name' AS first_name,
        u->>'$.last_name' AS last_name,
        u->>'$.email' AS email,
        u->>'$.role' AS role,
        CAST(u->>'$.permission_level' AS INTEGER) AS permission_level,
        u->>'$.url' AS user_url
    FROM stg_users;
""")

# Dim Projects
con.execute("""
    CREATE OR REPLACE TABLE dim_projects AS
    SELECT
        CAST(regexp_extract(p->>'$.url', '/projects/([0-9]+)$', 1) AS INTEGER) AS project_id,
        CAST(regexp_extract(p->>'$.contact', '/contacts/([0-9]+)$', 1) AS INTEGER) AS contact_id,
        p->>'$.name' AS project_name,
        p->>'$.status' AS status,
        p->>'$.budget_units' AS budget_units,
        CAST(p->>'$.budget' AS DECIMAL(18,2)) AS budget,
        CAST(p->>'$.normal_billing_rate' AS DECIMAL(18,2)) AS normal_billing_rate,
        p->>'$.billing_period' AS billing_period,
        p->>'$.url' AS project_url
    FROM stg_projects;
""")

print("Dimensions created: dim_contacts, dim_users, dim_projects.")

# -----------------------------------------------------------------------------
# 3. FACT TABLES: Sample JSON schema unnesting
# -----------------------------------------------------------------------------
print("\n--- Phase 3: Building Fact Tables ---")

# Fact Invoices (Header)
con.execute("""
    CREATE OR REPLACE TABLE fact_invoices AS
    SELECT
        CAST(regexp_extract(inv->>'$.url', '/invoices/([0-9]+)$', 1) AS INTEGER) AS invoice_id,
        CAST(regexp_extract(inv->>'$.contact', '/contacts/([0-9]+)$', 1) AS INTEGER) AS contact_id,
        CAST(regexp_extract(inv->>'$.project', '/projects/([0-9]+)$', 1) AS INTEGER) AS project_id,
        CAST(inv->>'$.dated_on' AS DATE) AS dated_on,
        CAST(inv->>'$.due_on' AS DATE) AS due_on,
        CAST(inv->>'$.payment_terms_in_days' AS INTEGER) AS payment_terms_in_days,
        inv->>'$.currency' AS currency,
        inv->>'$.status' AS status,
        CAST(inv->>'$.total_value' AS DECIMAL(18,2)) AS total_value,
        CAST(inv->>'$.paid_value' AS DECIMAL(18,2)) AS paid_value,
        CAST(inv->>'$.due_value' AS DECIMAL(18,2)) AS due_value
    FROM stg_invoices;
""")

# Fact Invoice Line Items (Unnesting deep array structure with sample JSON)
con.execute("""
    CREATE OR REPLACE TABLE fact_invoice_items AS
    SELECT
        CAST(regexp_extract(inv->>'$.url', '/invoices/([0-9]+)$', 1) AS INTEGER) AS invoice_id,
        item.description AS description,
        CAST(item.price AS DECIMAL(18,2)) AS unit_price,
        CAST(item.quantity AS DECIMAL(18,2)) AS quantity,
        CAST(item.sales_tax_rate AS DECIMAL(5,2)) AS sales_tax_rate,
        CAST(item.price AS DECIMAL(18,2)) * CAST(item.quantity AS DECIMAL(18,2)) AS gross_amount
    FROM stg_invoices
    CROSS JOIN unnest(
        from_json(
            inv->>'$.invoice_items', 
            '[{"description": "VARCHAR", "price": "VARCHAR", "quantity": "VARCHAR", "sales_tax_rate": "VARCHAR"}]'
        )
    ) AS t(item);
""")

# Fact Timeslips
con.execute("""
    CREATE OR REPLACE TABLE fact_timeslips AS
    SELECT
        CAST(regexp_extract(t->>'$.url', '/timeslips/([0-9]+)$', 1) AS INTEGER) AS timeslip_id,
        CAST(regexp_extract(t->>'$.user', '/users/([0-9]+)$', 1) AS INTEGER) AS user_id,
        CAST(regexp_extract(t->>'$.project', '/projects/([0-9]+)$', 1) AS INTEGER) AS project_id,
        CAST(regexp_extract(t->>'$.task', '/tasks/([0-9]+)$', 1) AS INTEGER) AS task_id,
        CAST(t->>'$.dated_on' AS DATE) AS dated_on,
        CAST(t->>'$.hours' AS DECIMAL(8,2)) AS hours,
        t->>'$.comment' AS comment
    FROM stg_timeslips;
""")

print("Fact tables created: fact_invoices, fact_invoice_items, fact_timeslips.")

con.close()
print("\nWarehouse successfully built! Database saved to 'warehouse.duckdb'.")