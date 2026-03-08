"""
Kernel Manager - Wrapper around jupyter_client for IPython kernel management.
Handles kernel lifecycle, code execution, and runtime context extraction.
"""

import asyncio
import json
import re
from typing import Optional, Any
from queue import Empty
import ast

from jupyter_client import KernelManager as JupyterKernelManager
from jupyter_client import KernelManager as JupyterKernelManager
from jupyter_client.kernelspec import KernelSpecManager
import os

# Define workspace dir if not imported to avoid circular imports
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")


class KernelSession:
    """Manages a single IPython kernel session."""
    
    def __init__(self):
        self.km: Optional[JupyterKernelManager] = None
        self.kc = None  # Kernel client
        self._running = False
        self.last_execution_result = {}  # Cache for context awareness

    @property
    def is_running(self) -> bool:
        return self._running and self.km is not None and self.km.is_alive()
    
    async def start(self) -> bool:
        """Start the kernel."""
        try:
            self.km = JupyterKernelManager()
            self.km.start_kernel(cwd=WORKSPACE_DIR)
            self.kc = self.km.client()
            self.kc.start_channels()
            
            # Wait for kernel to be ready
            try:
                self.kc.wait_for_ready(timeout=10)
            except RuntimeError:
                self.shutdown()
                return False
                
            self._running = True
            return True
        except Exception as e:
            print(f"Error starting kernel: {e}")
            return False

    async def shutdown(self):
        """Shutdown the kernel."""
        if self.kc:
            self.kc.stop_channels()
        if self.km:
            self.km.shutdown_kernel()
        self._running = False

    async def execute(
        self, 
        code: str, 
        silent: bool = False,
        timeout: float = 60.0
    ) -> dict:
        """
        Execute code in the kernel and return the result.
        
        Returns:
            {
                "status": "ok" | "error",
                "outputs": [...],  # stdout, display_data, etc.
                "error": {...}     # If status is "error"
            }
        """
        if not self.is_running:
            return {"status": "error", "error": {"message": "Kernel not running"}}
        
        try:
            # Send execute request
            msg_id = self.kc.execute(code, silent=silent, store_history=not silent)
            
            outputs = []
            status = "ok"
            error_info = None
            
            # Collect outputs with timeout
            deadline = asyncio.get_event_loop().time() + timeout
            
            while True:
                try:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        return {"status": "error", "error": {"message": "Execution timeout"}}
                    
                    # Check iopub channel for outputs
                    msg = self.kc.get_iopub_msg(timeout=min(0.5, remaining))
                    
                    if msg['parent_header'].get('msg_id') != msg_id:
                        continue
                    
                    msg_type = msg['msg_type']
                    content = msg['content']
                    
                    if msg_type == 'stream':
                        outputs.append({
                            "type": "stream",
                            "name": content.get('name', 'stdout'),
                            "text": content.get('text', '')
                        })
                    
                    elif msg_type == 'execute_result':
                        text = content.get('data', {}).get('text/plain', '')
                        outputs.append({
                            "type": "execute_result",
                            "data": content.get('data', {}),
                            "text": text
                        })
                    
                    elif msg_type == 'display_data':
                        outputs.append({
                            "type": "display_data",
                            "data": content.get('data', {})
                        })
                    
                    elif msg_type == 'error':
                        status = "error"
                        error_info = {
                            "ename": content.get('ename', 'Error'),
                            "evalue": content.get('evalue', ''),
                            "traceback": content.get('traceback', [])
                        }
                        outputs.append({
                            "type": "error",
                            "ename": error_info['ename'],
                            "evalue": error_info['evalue'],
                            "traceback": error_info['traceback']
                        })
                    
                    elif msg_type == 'status' and content.get('execution_state') == 'idle':
                        # Execution complete
                        break
                
                except Empty:
                    continue
            
            result = {
                "status": status,
                "outputs": outputs,
                "error": error_info
            }

            # Cache last meaningful execution (non-silent) for AI context
            if not silent:
                self.last_execution_result = result
            
            return result
        
        except Exception as e:
            return {
                "status": "error",
                "error": {"message": str(e)}
            }
    
    async def get_variables(self) -> list[str]:
        """Get list of variable names."""
        res = await self.execute("%who_ls", silent=True)
        if res.get("status") == "ok":
            for output in res.get("outputs", []):
                if output.get("type") == "execute_result":
                    try:
                        # %who_ls returns a list representation string
                        return ast.literal_eval(output.get("text", "[]"))
                    except:
                        pass
        return []

    async def get_variable_info(self, var_name: str) -> dict:
        """Get detailed info about a variable."""
        # Check type
        code = f"type({var_name}).__name__"
        res = await self.execute(code, silent=True)
        var_type = "unknown"
        if res.get("status") == "ok":
            for output in res.get("outputs", []):
                if output.get("type") == "execute_result":
                   var_type = output.get("text", "").strip("'\"")
        
        info = {"name": var_name, "type": var_type}

        # If it's a dataframe (pandas or similar), get shape and columns
        if "DataFrame" in var_type:
            code = f"{{'shape': {var_name}.shape, 'columns': list({var_name}.columns)}}"
            res = await self.execute(code, silent=True)
            if res.get("status") == "ok":
                for output in res.get("outputs", []):
                    if output.get("type") == "execute_result":
                        try:
                            details = ast.literal_eval(output.get("text", "{}"))
                            info["shape"] = str(details.get("shape", ""))
                            info["columns"] = details.get("columns", [])
                        except:
                            pass
        return info

    async def get_context(self) -> dict:
        """
        Extract full runtime context for AI assistance.
        Returns variable names, types, detailed info for DataFrames, AND last output.
        """
        variables = await self.get_variables()
        
        context = {
            "variables": [],
            "dataframes": [],
            "imports": [],
            "last_output": self.last_execution_result  # Include last execution result
        }
        
        for var_name in variables:
            # Skip private/magic variables
            if var_name.startswith('_'):
                continue
            
            info = await self.get_variable_info(var_name)
            context["variables"].append(info)
            
            if "DataFrame" in info.get("type", ""):
                context["dataframes"].append(info)
        
        # Get imported modules
        imports_result = await self.execute(
            "[name for name, val in globals().items() if isinstance(val, type(__builtins__))]",
            silent=True
        )
        for output in imports_result.get("outputs", []):
            if output.get("type") == "execute_result":
                try:
                    context["imports"] = eval(output.get("text", "[]"))
                except:
                    pass
        
        return context
    
    async def interrupt(self) -> bool:
        """Interrupt currently running code."""
        try:
            if self.km:
                self.km.interrupt_kernel()
                return True
        except Exception as e:
            print(f"Error interrupting kernel: {e}")
        return False


class KernelPool:
    """
    Manages multiple kernel sessions.
    In production, this would handle multiple users.
    """
    
    def __init__(self):
        self.sessions: dict[str, KernelSession] = {}
    
    async def create_session(self, session_id: str) -> KernelSession:
        """Create a new kernel session."""
        if session_id in self.sessions:
            await self.sessions[session_id].shutdown()
        
        session = KernelSession()
        success = await session.start()
        
        if success:
            self.sessions[session_id] = session
            return session
        
        raise RuntimeError("Failed to start kernel")
    
    def get_session(self, session_id: str) -> Optional[KernelSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)
    
    async def remove_session(self, session_id: str) -> bool:
        """Remove and shutdown a session."""
        if session_id in self.sessions:
            await self.sessions[session_id].shutdown()
            del self.sessions[session_id]
            return True
        return False
    
    async def shutdown_all(self):
        """Shutdown all sessions."""
        for session_id in list(self.sessions.keys()):
            await self.remove_session(session_id)


# Global kernel pool
kernel_pool = KernelPool()
