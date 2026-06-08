from .base import mcp_registry

@mcp_registry.register_tool(name="mcp_send_sms")
def send_sms(recipient: str, message: str):
    """Trigger dispatch of SMS message alert to supervisor, parent, or driver."""
    print(f"[Scalable MCP Notification] SMS sent to {recipient}: {message}")
    return {"status": "dispatched", "recipient": recipient, "channel": "SMS"}

@mcp_registry.register_tool(name="mcp_send_push")
def send_push(recipient: str, title: str, message: str):
    """Trigger push notification message dispatch to student/parent portal app."""
    print(f"[Scalable MCP Notification] Push sent to {recipient} [{title}]: {message}")
    return {"status": "dispatched", "recipient": recipient, "channel": "Push"}
