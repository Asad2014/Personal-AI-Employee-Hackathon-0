"""Facebook MCP Server — exposes tools to post, read, and get insights from a Facebook Page via Graph API."""

import asyncio
import json
import os

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'

server = Server("facebook-manager")


def _get_credentials() -> tuple[str, str]:
    """Return (access_token, page_id) from environment variables."""
    token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
    page_id = os.environ.get('FACEBOOK_PAGE_ID', '')
    if not token or not page_id:
        raise ValueError("FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID must be set")
    return token, page_id


def _api_get(endpoint: str, params: dict = None) -> dict:
    token, _ = _get_credentials()
    params = params or {}
    params['access_token'] = token
    resp = requests.get(f"{GRAPH_API_BASE}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _api_post(endpoint: str, data: dict = None) -> dict:
    token, _ = _get_credentials()
    data = data or {}
    data['access_token'] = token
    resp = requests.post(f"{GRAPH_API_BASE}/{endpoint}", data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="post_to_facebook",
        description=(
            "Publish a text post to the configured Facebook Page. "
            "IMPORTANT: All posts go through the approval workflow — only call "
            "this when processing approved items from the Approved/ folder."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The post content/message to publish",
                },
                "link": {
                    "type": "string",
                    "description": "Optional URL to include with the post",
                },
            },
            "required": ["message"],
        },
    ),
    Tool(
        name="get_page_insights",
        description=(
            "Get engagement insights for the Facebook Page — "
            "page views, post reach, engagement metrics. "
            "Useful for CEO Briefings and weekly reports."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period: day, week, days_28 (default: week)",
                    "enum": ["day", "week", "days_28"],
                    "default": "week",
                },
            },
        },
    ),
    Tool(
        name="list_page_posts",
        description="List recent posts from the Facebook Page with engagement stats.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of posts to return (default 10, max 50)",
                    "default": 10,
                },
            },
        },
    ),
    Tool(
        name="reply_to_comment",
        description=(
            "Reply to a comment on a Facebook Page post. "
            "IMPORTANT: For new/unknown contacts, create an approval file first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "The Facebook comment ID to reply to",
                },
                "message": {
                    "type": "string",
                    "description": "The reply text",
                },
            },
            "required": ["comment_id", "message"],
        },
    ),
    Tool(
        name="get_page_summary",
        description=(
            "Get a summary of the Facebook Page: name, followers, "
            "recent post count, and engagement overview. "
            "Great for dashboards and briefings."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def handle_post_to_facebook(arguments: dict) -> str:
    """Publish a post to the Facebook Page."""
    _, page_id = _get_credentials()
    data = {'message': arguments['message']}
    if arguments.get('link'):
        data['link'] = arguments['link']

    result = _api_post(f'{page_id}/feed', data)
    return json.dumps({"status": "published", "post_id": result.get('id', '')})


async def handle_get_page_insights(arguments: dict) -> str:
    """Fetch page insights/analytics."""
    _, page_id = _get_credentials()
    period = arguments.get('period', 'week')

    metrics = [
        'page_views_total',
        'page_engaged_users',
        'page_post_engagements',
        'page_impressions',
        'page_fan_adds',
    ]

    try:
        result = _api_get(f'{page_id}/insights', {
            'metric': ','.join(metrics),
            'period': period,
        })
        insights = {}
        for entry in result.get('data', []):
            name = entry.get('name', '')
            values = entry.get('values', [])
            if values:
                insights[name] = values[-1].get('value', 0)

        return json.dumps({"period": period, "insights": insights})
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        try:
            error_msg = e.response.json().get('error', {}).get('message', error_msg)
        except Exception:
            pass
        return json.dumps({"error": error_msg, "note": "Page insights require Page-level access token with read_insights permission"})


async def handle_list_page_posts(arguments: dict) -> str:
    """List recent page posts with engagement."""
    _, page_id = _get_credentials()
    limit = min(arguments.get('limit', 10), 50)

    result = _api_get(f'{page_id}/posts', {
        'fields': 'id,message,created_time,shares,likes.summary(true),comments.summary(true)',
        'limit': limit,
    })

    posts = []
    for post in result.get('data', []):
        posts.append({
            'id': post.get('id'),
            'message': (post.get('message', '') or '')[:200],
            'created_time': post.get('created_time', ''),
            'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
            'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0),
            'shares': post.get('shares', {}).get('count', 0),
        })

    return json.dumps({"posts": posts, "count": len(posts)})


async def handle_reply_to_comment(arguments: dict) -> str:
    """Reply to a comment on a page post."""
    comment_id = arguments['comment_id']
    message = arguments['message']

    result = _api_post(f'{comment_id}/comments', {'message': message})
    return json.dumps({"status": "replied", "reply_id": result.get('id', '')})


async def handle_get_page_summary(arguments: dict) -> str:
    """Get a summary overview of the Facebook Page."""
    _, page_id = _get_credentials()

    page_info = _api_get(page_id, {
        'fields': 'name,fan_count,followers_count,about,category,website,posts.limit(5){id,message,created_time}',
    })

    recent_posts = []
    for post in page_info.get('posts', {}).get('data', []):
        recent_posts.append({
            'id': post.get('id'),
            'message': (post.get('message', '') or '')[:100],
            'created_time': post.get('created_time', ''),
        })

    return json.dumps({
        "name": page_info.get('name', ''),
        "category": page_info.get('category', ''),
        "fan_count": page_info.get('fan_count', 0),
        "followers": page_info.get('followers_count', 0),
        "about": page_info.get('about', ''),
        "website": page_info.get('website', ''),
        "recent_posts": recent_posts,
    })


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "post_to_facebook": handle_post_to_facebook,
        "get_page_insights": handle_get_page_insights,
        "list_page_posts": handle_list_page_posts,
        "reply_to_comment": handle_reply_to_comment,
        "get_page_summary": handle_get_page_summary,
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
