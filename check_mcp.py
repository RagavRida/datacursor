import mcp
import inspect
print(dir(mcp))
try:
    import mcp.client
    print(dir(mcp.client))
except ImportError:
    print("No mcp.client")

try:
    from mcp.client.stdio import StdioServerParameters
    print("Found StdioServerParameters")
except ImportError:
    print("No StdioServerParameters")
