#!/usr/bin/env python3
"""
H3-Earth-State Remote Query Engine
Executes zero-download columnar SQL queries over HTTP against partitioned Parquet snapshots.
"""

import sys
import os
import argparse
import json
import logging
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_REPO = "mysukriramli/H3-Earth-State"
DEFAULT_BRANCH = "main"

def get_duckdb_connection():
    """Initializes in-memory DuckDB and configures httpfs for remote streaming."""
    con = duckdb.connect(database=":memory:")
    # httpfs enables HTTP/HTTPS range requests
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-east-1';")
    return con

def build_data_source_path(mode: str, repo: str, branch: str, year: str = "*", month: str = "*") -> str:
    """Builds the file glob pattern for either local filesystem or remote GitHub raw access."""
    if mode == "local":
        return f"snapshots/year={year}/month={month}/*.parquet"
    else:
        return f"https://raw.githubusercontent.com/{repo}/{branch}/snapshots/year={year}/month={month}/*.parquet"

def execute_query(sql_query: str, mode: str, repo: str, branch: str, output_format: str) -> str:
    """Executes SQL against targeted Parquet snapshots and formats the output."""
    con = get_duckdb_connection()
    source_path = build_data_source_path(mode, repo, branch)
    
    # Replace the placeholder {{SOURCE}} in the query with the actual path
    formatted_sql = sql_query.replace("{{SOURCE}}", f"'{source_path}'")
    
    logging.info(f"Target Source: {source_path}")
    logging.info(f"Executing SQL: {formatted_sql}")
    
    try:
        rel = con.execute(formatted_sql)
        
        if output_format == "json":
            df = rel.df()
            return df.to_json(orient="records", indent=2, date_format="iso")
        elif output_format == "markdown":
            df = rel.df()
            return df.to_markdown(index=False)
        elif output_format == "csv":
            df = rel.df()
            return df.to_csv(index=False)
        else: # Arrow/DuckDB native table format
            return str(rel.show())
    except Exception as e:
        return json.dumps({"error": f"Query execution failed: {str(e)}"})
    finally:
        con.close()

def main():
    parser = argparse.ArgumentParser(description="H3-Earth-State Remote SQL Query Engine for Agents")
    parser.add_argument("--mode", choices=["local", "remote"], default="local", help="Query local disk or remote GitHub URL")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in format owner/repo")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Target git branch (default: main)")
    parser.add_argument("--sql", help="Custom SQL query. Use {{SOURCE}} as the table identifier.")
    parser.add_argument("--h3", help="Shortcut: Query all historical records for a specific H3 hexagon ID")
    parser.add_argument("--anomalies-only", action="store_true", help="Shortcut: Query only high-impact physical disruptions")
    parser.add_argument("--format", choices=["json", "markdown", "csv", "table"], default="json", help="Output format")

    args = parser.parse_args()

    # Pre-packaged shortcuts for common agent use cases
    if args.h3:
        sql = f"""
            SELECT date, h3_res6_id, human_event_count, max_thermal_intensity_mw, 
                   max_seismic_magnitude, dominant_cameo_event_code
            FROM read_parquet({{SOURCE}})
            WHERE h3_res6_id = '{args.h3.strip()}'
            ORDER BY date DESC;
        """
    elif args.anomalies_only:
        sql = """
            SELECT date, h3_res6_id, human_event_count, max_thermal_intensity_mw, max_seismic_magnitude
            FROM read_parquet({{SOURCE}})
            WHERE max_seismic_magnitude >= 5.0 OR max_thermal_intensity_mw >= 80.0 OR human_event_count >= 100
            ORDER BY date DESC, max_seismic_magnitude DESC
            LIMIT 50;
        """
    elif args.sql:
        sql = args.sql
    else:
        # Default query: 5 most recent records
        sql = "SELECT * FROM read_parquet({{SOURCE}}) ORDER BY date DESC LIMIT 5;"

    result = execute_query(sql, args.mode, args.repo, args.branch, args.format)
    print(result)

if __name__ == "__main__":
    main()
