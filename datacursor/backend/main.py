"""
DataCursor Backend - FastAPI server with WebSocket for real-time kernel execution.
Supports multiple LLM providers: OpenAI, Anthropic, Google, Ollama (local).
"""

import os
import json
import uuid
import asyncio
from typing import Optional, Literal
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import shutil

from kernel_manager import kernel_pool, KernelSession
from llm_providers import llm_manager, ProviderType
from database_manager import db_manager

# Load environment variables
# Load environment variables
load_dotenv()

# Workspace Directory
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    print("🚀 DataCursor Backend starting...")
    
    # Initialize MCP servers in background
    async def init_mcp_servers():
        from mcp_client import mcp_client
        import sys
        python_path = sys.executable
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        
        print("Initializing MCP servers in background...")
        await mcp_client.connect_server(
            "kaggle",
            python_path,
            [os.path.join(backend_dir, "kaggle_mcp.py")]
        )
        await mcp_client.connect_server(
            "huggingface",
            python_path,
            [os.path.join(backend_dir, "hf_mcp.py")]
        )
        # Google BigQuery disabled - user doesn't have project ID
        # await mcp_client.connect_server(
        #     "google",
        #     python_path,
        #     [os.path.join(backend_dir, "google_mcp.py")]
        # )
        print("MCP server initialization complete!")
    
    # Start MCP initialization as a background task
    asyncio.create_task(init_mcp_servers())
    
    yield
    
    print("👋 Shutting down...")
    await kernel_pool.shutdown_all()
    
    # Shutdown MCP clients
    try:
        from mcp_client import mcp_client
        await mcp_client.shutdown()
    except:
        pass


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="DataCursor",
    description="AI-Native Data Science IDE Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MODELS
# =============================================================================

class KernelStartRequest(BaseModel):
    session_id: Optional[str] = None


class KernelStartResponse(BaseModel):
    session_id: str
    status: str


class ExecuteRequest(BaseModel):
    session_id: str
    code: str
    cell_id: Optional[str] = None


class AIRequest(BaseModel):
    session_id: str
    prompt: str
    current_code: str = ""
    cell_id: Optional[str] = None


class AIResponse(BaseModel):
    success: bool
    code: str
    diff: list[dict]
    error: Optional[str] = None


class SetAPIKeyRequest(BaseModel):
    api_key: str


class ProviderSettingsRequest(BaseModel):
    provider: Literal["openai", "anthropic", "google", "ollama", "groq", "openrouter"]
    api_key: Optional[str] = None
    model: Optional[str] = None


class OllamaModelRequest(BaseModel):
    model: str


class DatabaseConnectRequest(BaseModel):
    session_id: str
    name: str
    type: Literal["postgres", "mysql", "sqlite", "snowflake"]
    host: Optional[str] = "localhost"
    port: Optional[str] = ""
    user: Optional[str] = ""
    password: Optional[str] = ""
    database: Optional[str] = ""
    # Snowflake specific
    account: Optional[str] = None
    warehouse: Optional[str] = None
    schema_: Optional[str] = "PUBLIC"  # 'schema' is a reserved keyword in pydantic models sometimes


class DatabasePreviewRequest(BaseModel):
    session_id: str
    name: str
    query: str


# =============================================================================
# REST ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    return {"message": "DataCursor Backend", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/kernel/start", response_model=KernelStartResponse)
async def start_kernel(request: KernelStartRequest):
    """Start a new kernel session."""
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        session = await kernel_pool.create_session(session_id)
        return KernelStartResponse(
            session_id=session_id,
            status="running" if session.is_running else "error"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/kernel/shutdown")
async def shutdown_kernel(session_id: str):
    """Shutdown a kernel session."""
    success = await kernel_pool.remove_session(session_id)
    return {"success": success}


@app.post("/kernel/execute")
async def execute_code(request: ExecuteRequest):
    """Execute code in a kernel session."""
    session = kernel_pool.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await session.execute(request.code)
    return {
        "cell_id": request.cell_id,
        **result
    }


# =============================================================================
# FILE MANAGER ENDPOINTS
# =============================================================================

@app.get("/files/list")
async def list_files(path: str = "."):
    """List files in the current workspace."""
    try:
        # Resolve path relative to WORKSPACE_DIR
        base = WORKSPACE_DIR
        target = os.path.join(base, path)
        target = os.path.abspath(target)
        
        # Security check: Ensure target is within WORKSPACE_DIR
        if not target.startswith(base):
            raise HTTPException(status_code=403, detail="Access denied")
            
        if not os.path.exists(target):
             raise HTTPException(status_code=404, detail="Path not found")

        items = []
        for entry in os.scandir(target):
            if entry.name.startswith('.'): continue
            
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": os.path.relpath(entry.path, start=base), # Return relative path for frontend
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        return {"items": sorted(items, key=lambda x: (x["type"] != "directory", x["name"]))}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...), path: str = "."):
    """Upload a file to the workspace."""
    try:
        # Resolve target directory
        base = WORKSPACE_DIR
        target_dir = os.path.join(base, path)
        target_dir = os.path.abspath(target_dir)

        if not target_dir.startswith(base):
             raise HTTPException(status_code=403, detail="Access denied")

        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/rename")
async def rename_file(old_path: str, new_name: str):
    """Rename a file or directory."""
    try:
        base = WORKSPACE_DIR
        
        # Security: Prevent directory traversal
        if ".." in old_path or ".." in new_name or "/" in new_name or "\\" in new_name:
             raise HTTPException(status_code=400, detail="Invalid path or name")

        source = os.path.abspath(os.path.join(base, old_path))
        
        # Determine parent directory of source to keep it in same folder
        parent_dir = os.path.dirname(source)
        dest = os.path.abspath(os.path.join(parent_dir, new_name))

        # Check bounds
        if not source.startswith(base) or not dest.startswith(base):
             raise HTTPException(status_code=403, detail="Access denied")

        if not os.path.exists(source):
            raise HTTPException(status_code=404, detail="File not found")
            
        if os.path.exists(dest):
            raise HTTPException(status_code=409, detail="File already exists")

        os.rename(source, dest)
        return {"success": True}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/delete")
async def delete_file(path: str):
    """Delete a file or directory."""
    try:
        # Resolve target path
        base = WORKSPACE_DIR
        target = os.path.join(base, path)
        target = os.path.abspath(target)

        if not target.startswith(base):
             raise HTTPException(status_code=403, detail="Access denied")

        if os.path.isfile(target):
            os.remove(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        else:
            raise HTTPException(status_code=404, detail="path not found")
        return {"success": True}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/download")
async def download_file(path: str):
    """Download a file."""
    base = WORKSPACE_DIR
    target = os.path.join(base, path)
    target = os.path.abspath(target)
    
    if not target.startswith(base):
         raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)


@app.get("/kernel/context/{session_id}")
async def get_context(session_id: str):
    """Get runtime context for a session."""
    session = kernel_pool.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = await session.get_context()
    return context


@app.post("/ai/complete", response_model=AIResponse)
async def ai_complete(request: AIRequest):
    """Generate AI code completion with runtime context."""
    session = kernel_pool.get_session(request.session_id)
    
    # Get context if session exists
    context = None
    if session:
        context = await session.get_context()
    else:
        context = {}
    
    # Inject File and DB context
    try:
        # Get files from workspace
        files_list = []
        if os.path.exists(WORKSPACE_DIR):
            files_list = [f.name for f in os.scandir(WORKSPACE_DIR) if not f.name.startswith('.')]
        context["files"] = files_list
        
        # Get DB connections
        # NOTE: db_manager.get_connections returns list of dicts with 'name' and 'type'
        if session:
             context["database_connections"] = db_manager.get_connections(request.session_id)
    except Exception as e:
        print(f"Error injecting context: {e}")
    
    result = await llm_manager.generate_code(
        user_request=request.prompt,
        current_code=request.current_code,
        context=context
    )
    
    # Compute diff
    diff = []
    if result["success"]:
        from ai_bridge import ai_bridge
        diff = ai_bridge.compute_diff(request.current_code, result["code"])
    
    return AIResponse(
        success=result["success"],
        code=result["code"],
        diff=diff,
        error=result.get("error")
    )


@app.post("/ai/set-key")
async def set_api_key(request: SetAPIKeyRequest):
    """Set the AI API key for the active provider."""
    llm_manager.set_api_key(llm_manager.active_provider, request.api_key)
    return {"success": True}


# =============================================================================
# PROVIDER SETTINGS ENDPOINTS
# =============================================================================

@app.get("/settings/providers")
async def get_providers():
    """Get status of all LLM providers."""
    return {
        "providers": llm_manager.get_provider_status(),
        "active": llm_manager.active_provider.value,
        "data_scientist_mode": llm_manager.use_data_scientist_persona,
    }


@app.post("/settings/provider")
async def set_provider(request: ProviderSettingsRequest):
    """Set the active LLM provider."""
    try:
        provider = ProviderType(request.provider)
        
        # Set API key if provided
        if request.api_key:
            llm_manager.set_api_key(provider, request.api_key)
        
        # Set model for Ollama
        if provider == ProviderType.OLLAMA and request.model:
            llm_manager.set_ollama_model(request.model)
        
        llm_manager.set_active_provider(provider)
        
        return {
            "success": True,
            "active": provider.value,
            "configured": llm_manager.providers[provider].is_configured()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")


@app.post("/settings/data-scientist-mode")
async def set_data_scientist_mode(enabled: bool = True):
    """Enable/disable Data Scientist persona."""
    llm_manager.use_data_scientist_persona = enabled
    return {"success": True, "data_scientist_mode": enabled}


@app.get("/settings/ollama/models")
async def get_ollama_models():
    """Get available Ollama models."""
    ollama_provider = llm_manager.providers.get(ProviderType.OLLAMA)
    if ollama_provider:
        models = await ollama_provider.list_models()
        return {"models": models, "available": len(models) > 0}
    return {"models": [], "available": False}


# =============================================================================
# DATABASE ENDPOINTS
# =============================================================================

@app.post("/db/connect")
async def connect_database(request: DatabaseConnectRequest):
    """Connect to a database."""
    try:
        # Map schema_ to schema for snowflake
        kwargs = request.dict(exclude={"session_id", "name", "type", "schema_"})
        if request.schema_:
            kwargs["schema"] = request.schema_
            
        success = db_manager.connect(
            session_id=request.session_id,
            name=request.name,
            type=request.type,
            **kwargs
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/db/list/{session_id}")
async def list_databases(session_id: str):
    """List connected databases."""
    return {"databases": db_manager.get_connections(session_id)}


@app.get("/db/schema/{session_id}/{name}")
async def get_database_schema(session_id: str, name: str):
    """Get schema for a database."""
    try:
        return db_manager.get_schema(session_id, name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/db/preview")
async def preview_database_query(request: DatabasePreviewRequest):
    """Execute a read-only query preview."""
    try:
        results = db_manager.preview_query(request.session_id, request.name, request.query)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/db/disconnect/{session_id}/{name}")
async def disconnect_database(session_id: str, name: str):
    """Disconnect a database."""
    return {"success": db_manager.disconnect(session_id, name)}


# =============================================================================
# WEBSOCKET HANDLER
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time kernel interaction.
    
    Message Types:
    - execute: Run code in the kernel
    - ai_request: Get AI assistance with context
    - interrupt: Interrupt running code
    """
    await manager.connect(websocket, session_id)
    
    # Ensure kernel session exists
    session = kernel_pool.get_session(session_id)
    if not session:
        try:
            session = await kernel_pool.create_session(session_id)
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to create kernel: {str(e)}"
            })
            await websocket.close()
            return
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "execute":
                # Execute code
                cell_id = data.get("cellId")
                code = data.get("code", "")
                
                # Send execution started
                await manager.send_message(session_id, {
                    "type": "execution_started",
                    "cellId": cell_id
                })
                
                result = await session.execute(code)
                
                # Send result
                await manager.send_message(session_id, {
                    "type": "execution_result",
                    "cellId": cell_id,
                    **result
                })
            
            elif msg_type == "ai_request":
                # AI code generation
                cell_id = data.get("cellId")
                prompt = data.get("prompt", "")
                current_code = data.get("currentCode", "")
                
                # Get context
                context = await session.get_context()

                # Inject File and DB context
                try:
                    files_list = []
                    if os.path.exists(WORKSPACE_DIR):
                         files_list = [f.name for f in os.scandir(WORKSPACE_DIR) if not f.name.startswith('.')]
                    context["files"] = files_list
                    context["database_connections"] = db_manager.get_connections(session_id)
                except Exception as e:
                    print(f"Error injecting context in WS: {e}")
                
                # Generate code using LLM manager
                result = await llm_manager.generate_code(
                    user_request=prompt,
                    current_code=current_code,
                    context=context
                )
                
                # Compute diff
                diff = []
                if result["success"]:
                    from ai_bridge import ai_bridge
                    diff = ai_bridge.compute_diff(current_code, result["code"])
                
                await manager.send_message(session_id, {
                    "type": "ai_response",
                    "cellId": cell_id,
                    "success": result["success"],
                    "code": result["code"],
                    "diff": diff,
                    "error": result.get("error"),
                    "provider": llm_manager.active_provider.value
                })
            
            elif msg_type == "interrupt":
                # Interrupt execution
                await session.interrupt()
                await manager.send_message(session_id, {
                    "type": "interrupted"
                })
            
            elif msg_type == "get_context":
                # Get runtime context
                context = await session.get_context()
                await manager.send_message(session_id, {
                    "type": "context",
                    **context
                })
            
            elif msg_type == "ping":
                await manager.send_message(session_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
