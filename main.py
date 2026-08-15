"""
Orchestrator — runs the full Medallion pipeline: Bronze -> Silver -> Gold,
then runs data quality checks and exports the Gold tables to CSV for
easy inspection without needing a DuckDB client.
"""

import duckdb
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from bronze import load_bronze, DB_PATH
from silver import load_silver
from gold import load_gold
from data_quality import run_checks

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def export_gold_to_csv(con):
    for t in ["dim_customers", "dim_products", "fact_sales"]:
        df = con.execute(f"SELECT * FROM gold.{t}").fetchdf()
        path = os.path.join(OUTPUT_DIR, f"gold_{t}.csv")
        df.to_csv(path, index=False)
        print(f"  exported gold.{t} -> {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    con = duckdb.connect(DB_PATH)

    load_bronze(con)
    print()
    load_silver(con)
    print()
    load_gold(con)
    print()
    run_checks(con)

    print("\n" + "=" * 70)
    print("EXPORTING GOLD TABLES TO CSV")
    print("=" * 70)
    export_gold_to_csv(con)

    con.close()
    print(f"\nPipeline complete. Warehouse at {DB_PATH}")


if __name__ == "__main__":
    main()
