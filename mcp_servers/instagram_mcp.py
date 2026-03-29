"""Instagram MCP Server — exposes tools to post, read, and get insights from Instagram via Graph API."""

import asyncio
import json
import os

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'

server = Server("instagram-manager")


def _get_credentials() -> tuple[str, str]:
    """Return (access_token, ig_user_id) from environment variables."""
    token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
    ig_user_id = os.environ.get('INSTAGRAM_BUSINESS_ACCOUNT_ID', '')
    if not token or not ig_user_id:
        raise ValueError("FACEBOOK_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID must be set")
    return token, ig_user_id


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
        name="post_to_instagram",
        description=(
            "Create a photo post on Instagram. Requires image_url (publicly accessible). "
            "IMPORTANT: All posts go through the approval workflow — only call "
            "this when processing approved items from the Approved/ folder. "
            "Two-step process: creates media container, then publishes it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "Publicly accessible URL of the image to post",
                },
                "caption": {
                    "type": "string",
                    "description": "Optional caption/text for the post",
                },
            },
            "required": ["image_url"],
        },
    ),
    Tool(
        name="get_instagram_profile",
        description=(
            "Get Instagram profile info — username, followers count, "
            "following count, and media count."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="list_instagram_media",
        description="List recent Instagram posts with like and comment counts.",
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
        name="reply_to_instagram_comment",
        description=(
            "Reply to a comment on an Instagram post. "
            "IMPORTANT: For new/unknown contacts, create an approval file first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "The Instagram comment ID to reply to",
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
        name="get_instagram_insights",
        description=(
            "Get account-level insights for the Instagram Business account — "
            "impressions, reach, follower count. "
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
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def handle_post_to_instagram(arguments: dict) -> str:
    """Create and publish a photo post on Instagram (two-step container flow)."""
    _, ig_user_id = _get_credentials()

    # Step 1: Create media container
    container_data = {'image_url': arguments['image_url']}
    if arguments.get('caption'):
        container_data['caption'] = arguments['caption']

    container_result = _api_post(f'{ig_user_id}/media', container_data)
    creation_id = container_result.get('id')
    if not creation_id:
        return json.dumps({"error": "Failed to create media container", "response": container_result})

    # Step 2: Publish the container
    publish_result = _api_post(f'{ig_user_id}/media_publish', {'creation_id': creation_id})
    media_id = publish_result.get('id', '')

    return json.dumps({"status": "published", "media_id": media_id, "creation_id": creation_id})


async def handle_get_instagram_profile(arguments: dict) -> str:
    """Fetch Instagram profile information."""
    _, ig_user_id = _get_credentials()

    profile = _api_get(ig_user_id, {
        'fields': 'username,name,biography,followers_count,follows_count,media_count,profile_picture_url,website',
    })

    return json.dumps({
        "username": profile.get('username', ''),
        "name": profile.get('name', ''),
        "biography": profile.get('biography', ''),
        "followers": profile.get('followers_count', 0),
        "following": profile.get('follows_count', 0),
        "media_count": profile.get('media_count', 0),
        "profile_picture_url": profile.get('profile_picture_url', ''),
        "website": profile.get('website', ''),
    })


async def handle_list_instagram_media(arguments: dict) -> str:
    """List recent Instagram posts with engagement stats."""
    _, ig_user_id = _get_credentials()
    limit = min(arguments.get('limit', 10), 50)

    result = _api_get(f'{ig_user_id}/media', {
        'fields': 'id,caption,media_type,media_url,timestamp,like_count,comments_count,permalink',
        'limit': limit,
    })

    posts = []
    for post in result.get('data', []):
        posts.append({
            'id': post.get('id'),
            'caption': (post.get('caption', '') or '')[:200],
            'media_type': post.get('media_type', ''),
            'timestamp': post.get('timestamp', ''),
            'likes': post.get('like_count', 0),
            'comments': post.get('comments_count', 0),
            'permalink': post.get('permalink', ''),
        })

    return json.dumps({"posts": posts, "count": len(posts)})


async def handle_reply_to_instagram_comment(arguments: dict) -> str:
    """Reply to a comment on an Instagram post."""
    comment_id = arguments['comment_id']
    message = arguments['message']

    result = _api_post(f'{comment_id}/replies', {'message': message})
    return json.dumps({"status": "replied", "reply_id": result.get('id', '')})


async def handle_get_instagram_insights(arguments: dict) -> str:
    """Fetch account-level Instagram insights."""
    _, ig_user_id = _get_credentials()
    period = arguments.get('period', 'week')

    metrics = [
        'impressions',
        'reach',
        'follower_count',
    ]

    try:
        result = _api_get(f'{ig_user_id}/insights', {
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
        return json.dumps({"error": error_msg, "note": "Instagram insights require a Business or Creator account with appropriate permissions"})


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "post_to_instagram": handle_post_to_instagram,
        "get_instagram_profile": handle_get_instagram_profile,
        "list_instagram_media": handle_list_instagram_media,
        "reply_to_instagram_comment": handle_reply_to_instagram_comment,
        "get_instagram_insights": handle_get_instagram_insights,
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
