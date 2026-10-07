# query_warehouse.py - Runs analytical SQL queries against DuckDB

import duckdb

con = duckdb.connect("warehouse.duckdb")

print("\n--- Analytics Query 1: Top 5 Customers by Billed Revenue ---")
query_revenue = """
    SELECT 
        c.organisation_name,
        COUNT(f.invoice_id) AS total_invoices,
        SUM(f.total_value) AS total_revenue
    FROM fact_invoices f
    JOIN dim_contacts c ON f.contact_id = c.contact_id
    GROUP BY c.organisation_name
    ORDER BY total_revenue DESC
    LIMIT 5;
"""
print(con.sql(query_revenue))

print("\n--- Analytics Query 2: Staff Hours & Utilization by Project ---")
query_hours = """
    SELECT 
        p.project_name,
        u.first_name || ' ' || u.last_name AS employee_name,
        SUM(t.hours) AS total_hours_logged
    FROM fact_timeslips t
    JOIN dim_projects p ON t.project_id = p.project_id
    JOIN dim_users u ON t.user_id = u.user_id
    GROUP BY p.project_name, employee_name
    ORDER BY total_hours_logged DESC
    LIMIT 5;
"""
print(con.sql(query_hours))

print("\n--- Analytics Query 3: Invoice Line Item Breakdown ---")
query_items = """
    SELECT 
        i.description,
        COUNT(*) AS times_billed,
        AVG(i.unit_price) AS avg_unit_price,
        SUM(i.gross_amount) AS total_gross_billed
    FROM fact_invoice_items i
    GROUP BY i.description
    ORDER BY total_gross_billed DESC;
"""
print(con.sql(query_items))

con.close()