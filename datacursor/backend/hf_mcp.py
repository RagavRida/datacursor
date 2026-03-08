from mcp.server.fastmcp import FastMCP
import os
import json
from typing import List, Optional

# Check for Hugging Face token
if not os.environ.get("HF_TOKEN"):
    print("Warning: HF_TOKEN environment variable not set.")

# Initialize FastMCP server
mcp = FastMCP("Hugging Face DataCursor Integration")

@mcp.tool()
def search_models(query: str, limit: int = 5) -> str:
    """
    Search for models on Hugging Face Hub.
    
    Args:
        query: Search term
        limit: Max results
    """
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ.get("HF_TOKEN"))
        models = api.list_models(search=query, limit=limit, sort="downloads", direction=-1)
        
        results = []
        for m in models:
            results.append({
                "id": m.modelId,
                "downloads": m.downloads,
                "likes": m.likes,
                "task": m.pipeline_tag
            })
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching models: {str(e)}"

@mcp.tool()
def search_datasets(query: str, limit: int = 5) -> str:
    """
    Search for datasets on Hugging Face Hub.
    
    Args:
        query: Search term
        limit: Max results
    """
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ.get("HF_TOKEN"))
        datasets = api.list_datasets(search=query, limit=limit, sort="downloads", direction=-1)
        
        results = []
        for d in datasets:
            results.append({
                "id": d.datasetId,
                "downloads": d.downloads,
                "likes": d.likes
            })
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching datasets: {str(e)}"

@mcp.tool()
def preview_dataset(dataset_name: str, split: str = "train", limit: int = 5) -> str:
    """
    Preview rows from a Hugging Face dataset (streaming).
    
    Args:
        dataset_name: Name of the dataset (e.g. 'glue', 'squad')
        split: Split to load (default: 'train')
        limit: Number of rows to return
    """
    try:
        from datasets import load_dataset
        # Load in streaming mode to avoid downloading everything
        dataset = load_dataset(dataset_name, split=split, streaming=True, token=os.environ.get("HF_TOKEN"))
        
        rows = []
        for i, row in enumerate(dataset):
            if i >= limit:
                break
            rows.append(row)
            
        return json.dumps(rows, indent=2, default=str)
    except Exception as e:
        return f"Error loading dataset preview: {str(e)}"

if __name__ == "__main__":
    mcp.run()
