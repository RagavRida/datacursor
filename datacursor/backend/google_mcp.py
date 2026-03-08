from mcp.server.fastmcp import FastMCP
import json
import os
from typing import List, Optional

# Initialize FastMCP server
mcp = FastMCP("Google BigQuery DataCursor Integration")

def get_client():
    from google.cloud import bigquery
    # Expects GOOGLE_APPLICATION_CREDENTIALS or default auth
    return bigquery.Client()

@mcp.tool()
def list_public_datasets(limit: int = 10) -> str:
    """
    List featured Google Public Datasets from BigQuery.
    
    Args:
        limit: Max number of datasets to list
    """
    try:
        client = get_client()
        # Listing datasets from the 'bigquery-public-data' project
        datasets = list(client.list_datasets("bigquery-public-data", max_results=limit))
        
        results = []
        for d in datasets:
            results.append(d.dataset_id)
            
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error listing public datasets: {str(e)}"

@mcp.tool()
def get_table_schema(dataset_id: str, table_id: str) -> str:
    """
    Get schema for a specific table in bigquery-public-data.
    
    Args:
        dataset_id: e.g. 'usa_names'
        table_id: e.g. 'usa_1910_2013'
    """
    try:
        client = get_client()
        table_ref = f"bigquery-public-data.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        
        schema = []
        for field in table.schema:
            schema.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "description": field.description
            })
            
        return json.dumps(schema, indent=2)
    except Exception as e:
        return f"Error getting table schema: {str(e)}"

@mcp.tool()
def run_query(query: str) -> str:
    """
    Run a SQL query on BigQuery (ReadOnly/Public).
    WARNING: Only runs if query scans < 100MB to prevent accidental costs.
    
    Args:
        query: SQL query string
    """
    try:
        client = get_client()
        from google.cloud import bigquery
        
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=100 * 1024 * 1024  # 100 MB limit
        )
        
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()  # Waits for job to complete.
        
        df = results.to_dataframe()
        return df.to_json(orient="records", date_format="iso")
        
    except Exception as e:
        return f"Error running query: {str(e)}"

if __name__ == "__main__":
    mcp.run()
