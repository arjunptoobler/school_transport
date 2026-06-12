import logging
from .base import mcp

logger = logging.getLogger(__name__)


@mcp.tool(name="mcp_send_sms")
def send_sms(recipient: str, message: str) -> dict:
    """Trigger dispatch of SMS message alert to supervisor, parent, or driver."""
    logger.info(f"[MCP Notification] SMS → {recipient}: {message}")
    return {"status": "dispatched", "recipient": recipient, "channel": "SMS"}


@mcp.tool(name="mcp_send_push")
def send_push(recipient: str, title: str, message: str) -> dict:
    """Trigger push notification message dispatch to student/parent portal app."""
    logger.info(f"[MCP Notification] Push → {recipient} [{title}]: {message}")
    return {"status": "dispatched", "recipient": recipient, "channel": "Push"}


@mcp.tool(name="mcp_send_email")
def send_email(to: str, subject: str, body: str) -> dict:
    """Send a formal compliance or enforcement email to an authority, operator, or driver."""
    logger.info(f"[MCP Notification] Email → {to} [{subject}]")
    return {"status": "sent", "to": to, "channel": "Email"}
