import inspect
from typing import Callable, Dict, Any

class MCPToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str = None):
        """Decorator to register functions as MCP tools."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            return func
        return decorator

    def call_tool(self, name: str, *args, **kwargs) -> Any:
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return self.tools[name](*args, **kwargs)

# Singleton global registry representing MCP host environment
mcp_registry = MCPToolRegistry()
