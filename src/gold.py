"""
Gold Layer — Business-Ready Star Schema
==========================================
Builds a dimensional model on top of Silver:

  dim_customers  : one row per customer, CRM as the base, enriched with
                    ERP birthdate/gender/country. Where CRM and ERP
                    disagree on gender, CRM wins (source of truth for
                    account data) and ERP fills the gaps CRM left null.
  dim_products   : current product catalog only (prd_end_dt IS NULL),
                    joined to its category/subcategory from ERP.
  fact_sales     : one row per sales line, resolved to surrogate keys.
"""

import duckdb
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "warehouse.duckdb")

DIM_CUSTOMERS_SQL = """
CREATE OR REPLACE TABLE gold.dim_customers AS
SELECT
    ROW_NUMBER() OVER (ORDER BY ci.cst_id) AS customer_key,
    ci.cst_id                              AS customer_id,
    ci.cst_key                             AS customer_number,
    ci.cst_firstname                       AS first_name,
    ci.cst_lastname                        AS last_name,
    la.cntry                               AS country,
    ci.cst_marital_status                  AS marital_status,
    CASE WHEN ci.cst_gndr <> 'n/a' THEN ci.cst_gndr
         ELSE COALESCE(ca.gen, 'n/a') END  AS gender,
    ca.bdate                               AS birth_date,
    ci.cst_create_date                     AS create_date
FROM silver.crm_cust_info ci
LEFT JOIN silver.erp_cust_az12 ca ON ci.cst_key = ca.cid
LEFT JOIN silver.erp_loc_a101  la ON ci.cst_key = la.cid;
"""

DIM_PRODUCTS_SQL = """
CREATE OR REPLACE TABLE gold.dim_products AS
SELECT
    ROW_NUMBER() OVER (ORDER BY pn.prd_start_dt, pn.prd_key) AS product_key,
    pn.prd_id                                                AS product_id,
    pn.prd_key                                                AS product_number,
    pn.prd_nm                                                AS product_name,
    pn.cat_id                                                AS category_id,
    pc.cat                                                    AS category,
    pc.subcat                                                 AS subcategory,
    pc.maintenance                                            AS maintenance,
    pn.prd_cost                                               AS cost,
    pn.prd_line                                               AS product_line,
    pn.prd_start_dt                                           AS start_date
FROM silver.crm_prd_info pn
LEFT JOIN silver.erp_px_cat_g1v2 pc ON pn.cat_id = pc.id
WHERE pn.prd_end_dt IS NULL;  -- current products only
"""

FACT_SALES_SQL = """
CREATE OR REPLACE TABLE gold.fact_sales AS
SELECT
    sd.sls_ord_num  AS order_number,
    dp.product_key,
    dc.customer_key,
    sd.sls_order_dt AS order_date,
    sd.sls_ship_dt  AS ship_date,
    sd.sls_due_dt   AS due_date,
    sd.sls_sales    AS sales_amount,
    sd.sls_quantity AS quantity,
    sd.sls_price    AS price
FROM silver.crm_sales_details sd
LEFT JOIN gold.dim_products  dp ON sd.sls_prd_key = dp.product_number
LEFT JOIN gold.dim_customers dc ON sd.sls_cust_id  = dc.customer_id;
"""


def load_gold(con: duckdb.DuckDBPyConnection):
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    print("=" * 70)
    print("GOLD LAYER — business-ready star schema")
    print("=" * 70)
    con.execute(DIM_CUSTOMERS_SQL)
    con.execute(DIM_PRODUCTS_SQL)
    con.execute(FACT_SALES_SQL)

    for t in ["dim_customers", "dim_products", "fact_sales"]:
        n = con.execute(f"SELECT COUNT(*) FROM gold.{t}").fetchone()[0]
        print(f"  gold.{t:<20} -> {n:>6} rows")


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH)
    load_gold(con)
    con.close()
    print("\nGold layer built ->", DB_PATH)
