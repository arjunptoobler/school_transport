"""
ADEK School Transport MCP Server

Exposes all domain tools over the MCP stdio transport.
Run as a subprocess via: python -m backend.mcp.server
"""

from .base import mcp

# Importing each module registers its @mcp.tool() functions with the FastMCP instance
from . import driver, fleet, incident, compliance, evidence, notification, route, policy

if __name__ == "__main__":
    mcp.run()
