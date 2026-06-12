"""
MCP subprocess client — manages a single persistent MCP server process
and exposes a synchronous call_tool() interface for agent code.
"""

import asyncio
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

_PROJECT_ROOT = str(Path(__file__).parents[2])  # .../school_transport/


class _MCPSubprocessClient:
    """Manages one persistent MCP server subprocess with a dedicated event loop thread."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._session: ClientSession | None = None
        self._shutdown: asyncio.Event | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="mcp-server-loop")
        self._thread.start()
        if not self._ready.wait(timeout=20):
            raise RuntimeError("MCP server subprocess did not become ready within 20 seconds")

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._lifecycle())

    async def _lifecycle(self):
        existing_pythonpath = os.environ.get("PYTHONPATH", "")
        pythonpath = f"{_PROJECT_ROOT}:{existing_pythonpath}" if existing_pythonpath else _PROJECT_ROOT
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "backend.mcp.server"],
            cwd=_PROJECT_ROOT,
            env={**os.environ, "PYTHONPATH": pythonpath},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                self._shutdown = asyncio.Event()
                self._ready.set()
                logger.info("MCP server subprocess ready")
                await self._shutdown.wait()   # Keeps context managers alive until shutdown

    def call_tool(self, name: str, **kwargs) -> Any:
        if self._session is None:
            raise RuntimeError("MCP client not initialized")
        future = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(name, arguments=kwargs),
            self._loop,
        )
        result = future.result(timeout=30)
        if result.isError:
            err = result.content[0].text if result.content else "Unknown MCP error"
            return {"error": err}
        if not result.content:
            return {}
        if len(result.content) == 1:
            # Single item — tool returned a scalar or dict
            try:
                return json.loads(result.content[0].text)
            except (json.JSONDecodeError, AttributeError):
                return {"result": str(result.content[0])}
        else:
            # Multiple items — FastMCP serialized a list (one TextContent per element)
            items = []
            for c in result.content:
                try:
                    items.append(json.loads(c.text))
                except (json.JSONDecodeError, AttributeError):
                    items.append({"result": str(c)})
            return items


# ── Lazy singleton ──────────────────────────────────────────────────────────

_instance: _MCPSubprocessClient | None = None
_lock = threading.Lock()


def _get_instance() -> _MCPSubprocessClient:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = _MCPSubprocessClient()
    return _instance


class _ClientProxy:
    """Drop-in replacement for the old mcp_registry — same .call_tool() interface."""

    def call_tool(self, name: str, **kwargs) -> Any:
        return _get_instance().call_tool(name, **kwargs)


mcp_client = _ClientProxy()
