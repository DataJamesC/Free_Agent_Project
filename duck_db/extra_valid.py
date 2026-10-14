# validate_warehouse.py - Validation & Data Quality Checks for DuckDB Warehouse

import duckdb

con = duckdb.connect("warehouse.duckdb")

# -----------------------------------------------------------------------------
# 1. Validation Query: Active Projects for a Specific Client
# -----------------------------------------------------------------------------
# Change 'Client 1' or 'Acme' to match a specific organisation name in your database
target_company = "Client 1 Corp"

print(f"--- 1. Active Projects Attached to Client Matching '{target_company}' ---")
query_specific_client = f"""
    SELECT 
        c.contact_id,
        c.organisation_name,
        p.project_id,
        p.project_name,
        p.status AS project_status,
        p.budget,
        p.budget_units
    FROM dim_projects p
    JOIN dim_contacts c ON p.contact_id = c.contact_id
    WHERE LOWER(p.status) = 'active'
      AND c.organisation_name ILIKE '%{target_company}%'
    ORDER BY c.organisation_name, p.project_name;
"""

result = con.sql(query_specific_client)
print(result)

# -----------------------------------------------------------------------------
# 2. Validation Query: Active Project Counts Grouped Across All Clients
# -----------------------------------------------------------------------------
print("\n--- 2. Active Projects Summary (Top 10 Clients by Active Project Count) ---")
query_summary = """
    SELECT 
        c.contact_id,
        c.organisation_name,
        COUNT(p.project_id) AS total_active_projects
    FROM dim_contacts c
    LEFT JOIN dim_projects p 
        ON c.contact_id = p.contact_id 
       AND LOWER(p.status) = 'active'
    GROUP BY c.contact_id, c.organisation_name
    HAVING total_active_projects > 0
    ORDER BY total_active_projects DESC, c.organisation_name
    LIMIT 10;
"""

print(con.sql(query_summary))

# -----------------------------------------------------------------------------
# 3. Data Quality Check: Verify Foreign Key Integrity Between Projects & Contacts
# -----------------------------------------------------------------------------
print("\n--- 3. Data Quality Check: Projects with Missing/Invalid Contacts ---")
query_orphans = """
    SELECT 
        p.project_id,
        p.project_name,
        p.contact_id
    FROM dim_projects p
    LEFT JOIN dim_contacts c ON p.contact_id = c.contact_id
    WHERE c.contact_id IS NULL;
"""

orphans = con.sql(query_orphans)
if len(orphans) == 0:
    print(" PASSED: All projects correctly resolve to valid contacts in dim_contacts.")
else:
    print(" FAILED: Found orphan projects with invalid contact_ids:")
    print(orphans)

con.close()