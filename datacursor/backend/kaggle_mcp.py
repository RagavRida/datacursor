from mcp.server.fastmcp import FastMCP
import os
import json
from typing import List, Optional

# Initialize FastMCP server
mcp = FastMCP("Kaggle DataCursor Integration")

def get_api():
    """Get authenticated Kaggle API instance."""
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    return api

@mcp.tool()
def search_datasets(query: str, page: int = 1) -> str:
    """
    Search for datasets on Kaggle.
    
    Args:
        query: Search term
        page: Page number
    """
    try:
        api = get_api()
        datasets = api.dataset_list(search=query, page=page)
        
        results = []
        for d in datasets:
            results.append({
                "ref": d.ref,
                "title": d.title,
                "size": d.size,
                "lastUpdated": str(d.lastUpdated),
                "downloadCount": d.downloadCount,
                "voteCount": d.voteCount
            })
        
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching datasets: {str(e)}"

@mcp.tool()
def search_competitions(query: str, page: int = 1) -> str:
    """
    Search for Kaggle competitions.
    
    Args:
        query: Search term
        page: Page number
    """
    try:
        api = get_api()
        competitions = api.competitions_list(search=query, page=page)
        
        results = []
        for c in competitions:
            results.append({
                "ref": c.ref,
                "title": c.title,
                "description": c.description,
                "category": c.category,
                "reward": c.reward,
                "deadline": str(c.deadline)
            })
            
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching competitions: {str(e)}"

@mcp.tool()
def download_dataset(dataset_ref: str, path: str = "./workspace/data") -> str:
    """
    Download files from a Kaggle dataset.
    
    Args:
        dataset_ref: Dataset reference (e.g. 'zillow/zecon')
        path: Destination path relative to current directory
    """
    try:
        api = get_api()
        os.makedirs(path, exist_ok=True)
        
        # Check if dataset exists first to avoid vague errors
        # (Implicitly handled by download call usually, but good to be safe)
        
        api.dataset_download_files(dataset_ref, path=path, unzip=True)
        return f"Successfully downloaded {dataset_ref} to {path}"
    except Exception as e:
        return f"Error downloading dataset: {str(e)}"

@mcp.tool()
def get_kernel_output(kernel_ref: str) -> str:
    """
    Get the output of a specific kernel.
    
    Args:
        kernel_ref: Kernel reference (user/repo)
    """
    try:
        api = get_api()
        # This is a simplification; authentic kernel interaction is more complex
        # but this serves as a basic retrieval hook
        status = api.kernel_status(kernel_ref)
        return json.dumps(status, indent=2)
    except Exception as e:
        return f"Error getting kernel info: {str(e)}"

if __name__ == "__main__":
    # Run the server via stdio
    mcp.run()
