"""
Data Quality Checks — run after each layer to catch regressions.
Fails loudly (prints FAIL) rather than silently passing bad data downstream.
"""

import duckdb


def run_checks(con: duckdb.DuckDBPyConnection):
    print("=" * 70)
    print("DATA QUALITY CHECKS")
    print("=" * 70)
    results = []

    def check(name, sql, expect_zero=True):
        val = con.execute(sql).fetchone()[0]
        ok = (val == 0) if expect_zero else (val > 0)
        status = "PASS" if ok else "FAIL"
        results.append((status, name, val))
        print(f"  [{status}] {name}: {val}")

    # Silver checks
    check("silver.crm_cust_info has no duplicate cst_id",
          "SELECT COUNT(*) - COUNT(DISTINCT cst_id) FROM silver.crm_cust_info")
    check("silver.crm_sales_details: sales = quantity * price (violations)",
          "SELECT COUNT(*) FROM silver.crm_sales_details "
          "WHERE ROUND(sls_sales,2) <> ROUND(sls_quantity * sls_price, 2)")
    check("silver.crm_prd_info: negative cost", "SELECT COUNT(*) FROM silver.crm_prd_info WHERE prd_cost < 0")

    # Gold referential integrity
    check("gold.fact_sales: rows with no matching customer_key",
          "SELECT COUNT(*) FROM gold.fact_sales WHERE customer_key IS NULL")
    check("gold.fact_sales: rows with no matching product_key",
          "SELECT COUNT(*) FROM gold.fact_sales WHERE product_key IS NULL")
    check("gold.dim_customers: duplicate customer_key",
          "SELECT COUNT(*) - COUNT(DISTINCT customer_key) FROM gold.dim_customers")
    check("gold.dim_products: duplicate product_key",
          "SELECT COUNT(*) - COUNT(DISTINCT product_key) FROM gold.dim_products")

    n_fail = sum(1 for r in results if r[0] == "FAIL")
    print(f"\n{len(results) - n_fail}/{len(results)} checks passed.")
    return results


if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "warehouse.duckdb")
    con = duckdb.connect(DB_PATH)
    run_checks(con)
    con.close()
