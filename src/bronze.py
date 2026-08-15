"""
Bronze Layer — Raw Ingestion
=============================
Loads source CRM and ERP CSVs into DuckDB exactly as-is, with zero
transformation. The Bronze layer is the system of record for "what did
we actually receive from the source" and exists so every downstream
issue can always be traced back to raw input.
"""

import duckdb
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "warehouse.duckdb")

SOURCES = {
    "bronze.crm_cust_info": f"{DATA_DIR}/source_crm/cust_info.csv",
    "bronze.crm_prd_info": f"{DATA_DIR}/source_crm/prd_info.csv",
    "bronze.crm_sales_details": f"{DATA_DIR}/source_crm/sales_details.csv",
    "bronze.erp_cust_az12": f"{DATA_DIR}/source_erp/CUST_AZ12.csv",
    "bronze.erp_loc_a101": f"{DATA_DIR}/source_erp/LOC_A101.csv",
    "bronze.erp_px_cat_g1v2": f"{DATA_DIR}/source_erp/PX_CAT_G1V2.csv",
}


def load_bronze(con: duckdb.DuckDBPyConnection):
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    print("=" * 70)
    print("BRONZE LAYER — raw ingestion")
    print("=" * 70)
    for table, path in SOURCES.items():
        df = pd.read_csv(path)
        df["_ingested_at"] = pd.Timestamp.now()
        df["_source_file"] = os.path.basename(path)
        con.register("tmp_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM tmp_df;")
        con.unregister("tmp_df")
        print(f"  {table:<28} <- {os.path.basename(path):<20} ({len(df):>6} rows)")


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH)
    load_bronze(con)
    con.close()
    print("\nBronze layer loaded ->", DB_PATH)
