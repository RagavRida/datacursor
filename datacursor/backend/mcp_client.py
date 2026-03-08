"""
MCP Client - Manages connections to MCP servers and provides tool access.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


class McpClient:
    """Client for connecting to MCP servers via stdio."""
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.available_tools: Dict[str, Dict] = {}
        self._connections: Dict[str, Any] = {}
    
    async def connect_server(self, name: str, command: str, args: List[str] = None):
        """
        Connect to an MCP server.
        
        Args:
            name: Server identifier
            command: Command to run (e.g., 'python3')
            args: Arguments (e.g., ['kaggle_mcp.py'])
        """
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            server_params = StdioServerParameters(
                command=command,
                args=args or [],
                env=None
            )
            
            # Create stdio client and store the context manager
            stdio_context = stdio_client(server_params)
            read, write = await stdio_context.__aenter__()
            
            # Store context for cleanup
            self._connections[name] = stdio_context
            
            # Create session
            session = ClientSession(read, write)
            await session.initialize()
            
            # List available tools
            tools_response = await session.list_tools()
            
            self.servers[name] = {
                'session': session,
                'read': read,
                'write': write
            }
            
            # Store tools with server reference
            for tool in tools_response.tools:
                tool_key = f"{name}.{tool.name}"
                self.available_tools[tool_key] = {
                    "server": name,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
            
            print(f"✓ Connected to MCP server '{name}' with {len(tools_response.tools)} tools")
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to MCP server '{name}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def call_tool(self, tool_key: str, arguments: Dict[str, Any]) -> Optional[str]:
        """
        Call a tool on the appropriate MCP server.
        
        Args:
            tool_key: Tool identifier in format 'server.tool_name'
            arguments: Tool arguments
            
        Returns:
            Tool result as string
        """
        if tool_key not in self.available_tools:
            return f"Error: Tool '{tool_key}' not found"
        
        tool_info = self.available_tools[tool_key]
        server_name = tool_info["server"]
        tool_name = tool_info["name"]
        
        server_info = self.servers.get(server_name)
        if not server_info:
            return f"Error: Server '{server_name}' not connected"
        
        session = server_info['session']
        
        try:
            result = await session.call_tool(tool_name, arguments=arguments)
            
            # Extract text content from result
            if hasattr(result, 'content') and result.content:
                return '\n'.join(
                    item.text for item in result.content if hasattr(item, 'text')
                )
            return str(result)
            
        except Exception as e:
            return f"Error calling tool: {str(e)}"
    
    def get_tools_schema(self) -> List[Dict]:
        """
        Get OpenAI-compatible tools schema for all available tools.
        
        Returns:
            List of tool schemas
        """
        schemas = []
        for tool_key, tool_info in self.available_tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool_key.replace('.', '_'),  # Replace dots for compatibility
                    "description": tool_info["description"] or "",
                    "parameters": tool_info["input_schema"] or {"type": "object", "properties": {}}
                }
            })
        return schemas
    
    async def shutdown(self):
        """Close all server connections."""
        for name, context in self._connections.items():
            try:
                await context.__aexit__(None, None, None)
                print(f"Disconnected from '{name}'")
            except Exception as e:
                print(f"Error disconnecting from '{name}': {e}")


# Global MCP client instance
mcp_client = McpClient()
