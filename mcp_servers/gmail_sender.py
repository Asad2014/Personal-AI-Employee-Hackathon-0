"""Gmail MCP Server — exposes send_email, draft_email, and list_drafts tools to Claude Code."""

import asyncio
import base64
import json
import os
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

server = Server("gmail-sender")


def get_gmail_service():
    """Authenticate and return a Gmail API service with read+send scopes."""
    credentials_path = Path(
        os.environ.get("GMAIL_CREDENTIALS_PATH", "./credentials.json")
    )
    token_path = Path(os.environ.get("GMAIL_TOKEN_PATH", "./token.json"))

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="send_email",
        description=(
            "Send an email via Gmail. Returns the sent message ID. "
            "IMPORTANT: For new/unknown contacts, create an approval file in "
            "Pending_Approval/ first — do NOT call this tool until the human approves."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "Plain-text email body",
                },
                "cc": {
                    "type": "string",
                    "description": "CC email address (optional)",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC email address (optional)",
                },
                "in_reply_to": {
                    "type": "string",
                    "description": "Gmail message ID to reply to (optional, sets threading headers)",
                },
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="draft_email",
        description=(
            "Create a Gmail draft without sending it. Useful when an email "
            "needs human approval before sending. Returns the draft ID."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "Plain-text email body",
                },
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="list_drafts",
        description="List recent Gmail drafts. Returns draft IDs, recipients, and subjects.",
        inputSchema={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of drafts to return (default 10)",
                    "default": 10,
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def handle_send_email(arguments: dict) -> str:
    """Build a MIME message and send it via the Gmail API."""
    service = get_gmail_service()

    msg = MIMEText(arguments["body"])
    msg["to"] = arguments["to"]
    msg["subject"] = arguments["subject"]
    if arguments.get("cc"):
        msg["cc"] = arguments["cc"]
    if arguments.get("bcc"):
        msg["bcc"] = arguments["bcc"]

    # Threading: if replying to an existing message, set In-Reply-To and References
    if arguments.get("in_reply_to"):
        try:
            original = (
                service.users()
                .messages()
                .get(userId="me", id=arguments["in_reply_to"], format="metadata",
                     metadataHeaders=["Message-ID", "References"])
                .execute()
            )
            headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
            if "Message-ID" in headers:
                msg["In-Reply-To"] = headers["Message-ID"]
                msg["References"] = headers.get("References", "") + " " + headers["Message-ID"]
        except Exception:
            pass  # send without threading if lookup fails

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"raw": raw}

    # If replying, set threadId for Gmail threading
    if arguments.get("in_reply_to"):
        try:
            original_msg = (
                service.users()
                .messages()
                .get(userId="me", id=arguments["in_reply_to"], format="minimal")
                .execute()
            )
            body["threadId"] = original_msg.get("threadId")
        except Exception:
            pass

    sent = service.users().messages().send(userId="me", body=body).execute()
    return json.dumps({"status": "sent", "message_id": sent["id"]})


async def handle_draft_email(arguments: dict) -> str:
    """Create a Gmail draft."""
    service = get_gmail_service()

    msg = MIMEText(arguments["body"])
    msg["to"] = arguments["to"]
    msg["subject"] = arguments["subject"]

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )
    return json.dumps({"status": "draft_created", "draft_id": draft["id"]})


async def handle_list_drafts(arguments: dict) -> str:
    """List recent Gmail drafts."""
    service = get_gmail_service()
    max_results = arguments.get("max_results", 10)

    results = (
        service.users().drafts().list(userId="me", maxResults=max_results).execute()
    )
    drafts = results.get("drafts", [])

    entries = []
    for d in drafts:
        draft_msg_id = d.get("message", {}).get("id", "")
        headers = {}
        if draft_msg_id:
            msg_detail = (
                service.users()
                .messages()
                .get(userId="me", id=draft_msg_id, format="metadata",
                     metadataHeaders=["To", "Subject"])
                .execute()
            )
            headers = {
                h["name"]: h["value"]
                for h in msg_detail.get("payload", {}).get("headers", [])
            }
        entries.append(
            {
                "draft_id": d["id"],
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
            }
        )

    return json.dumps({"drafts": entries, "count": len(entries)})


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "send_email": handle_send_email,
        "draft_email": handle_draft_email,
        "list_drafts": handle_list_drafts,
    }

    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
