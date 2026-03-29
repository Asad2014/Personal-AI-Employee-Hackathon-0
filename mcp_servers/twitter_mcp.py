"""Twitter/X MCP Server — exposes tools to post tweets, read profile, list tweets, search mentions, and reply via Twitter API v2."""

import asyncio
import json
import os

import requests
from requests_oauthlib import OAuth1
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

TWITTER_API_BASE = 'https://api.twitter.com/2'

server = Server("twitter-manager")


def _get_oauth1() -> OAuth1:
    """Return an OAuth1 auth object for user-context requests (posting, replying)."""
    consumer_key = os.environ.get('TWITTER_API_KEY', '')
    consumer_secret = os.environ.get('TWITTER_API_SECRET', '')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN', '')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise ValueError(
            "TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, "
            "and TWITTER_ACCESS_TOKEN_SECRET must all be set"
        )
    return OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)


def _get_bearer_headers() -> dict:
    """Return Authorization header dict for app-only (Bearer token) requests."""
    bearer = os.environ.get('TWITTER_BEARER_TOKEN', '')
    if not bearer:
        raise ValueError("TWITTER_BEARER_TOKEN must be set")
    return {"Authorization": f"Bearer {bearer}"}


def _get_user_id() -> str:
    """Fetch the authenticated user's ID using the Bearer token."""
    headers = _get_bearer_headers()
    resp = requests.get(f"{TWITTER_API_BASE}/users/me", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()['data']['id']


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="post_tweet",
        description=(
            "Post a tweet to Twitter/X (max 280 characters). "
            "IMPORTANT: All tweets go through the approval workflow — only call "
            "this when processing approved items from the Approved/ folder."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The tweet text (max 280 characters)",
                    "maxLength": 280,
                },
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="get_twitter_profile",
        description=(
            "Get the authenticated Twitter/X user's profile info — "
            "username, name, bio, follower/following counts, tweet count."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="list_recent_tweets",
        description="List the authenticated user's recent tweets with engagement metrics.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of tweets to return (default 10, max 100)",
                    "default": 10,
                },
            },
        },
    ),
    Tool(
        name="search_mentions",
        description="Search for recent mentions of the authenticated user on Twitter/X.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of mentions to return (default 10, max 100)",
                    "default": 10,
                },
            },
        },
    ),
    Tool(
        name="reply_to_tweet",
        description=(
            "Reply to a specific tweet on Twitter/X. "
            "IMPORTANT: For new/unknown contacts, create an approval file first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "tweet_id": {
                    "type": "string",
                    "description": "The ID of the tweet to reply to",
                },
                "text": {
                    "type": "string",
                    "description": "The reply text (max 280 characters)",
                    "maxLength": 280,
                },
            },
            "required": ["tweet_id", "text"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def handle_post_tweet(arguments: dict) -> str:
    """Post a tweet via Twitter API v2."""
    text = arguments['text']
    if len(text) > 280:
        return json.dumps({"error": f"Tweet exceeds 280 characters ({len(text)} chars)"})

    auth = _get_oauth1()
    resp = requests.post(
        f"{TWITTER_API_BASE}/tweets",
        json={"text": text},
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    tweet_id = result.get('data', {}).get('id', '')
    return json.dumps({"status": "published", "tweet_id": tweet_id})


async def handle_get_twitter_profile(arguments: dict) -> str:
    """Fetch the authenticated user's profile information."""
    headers = _get_bearer_headers()
    resp = requests.get(
        f"{TWITTER_API_BASE}/users/me",
        params={"user.fields": "public_metrics,description,profile_image_url,created_at"},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get('data', {})
    metrics = data.get('public_metrics', {})

    return json.dumps({
        "id": data.get('id', ''),
        "username": data.get('username', ''),
        "name": data.get('name', ''),
        "description": data.get('description', ''),
        "followers": metrics.get('followers_count', 0),
        "following": metrics.get('following_count', 0),
        "tweet_count": metrics.get('tweet_count', 0),
        "listed_count": metrics.get('listed_count', 0),
        "created_at": data.get('created_at', ''),
        "profile_image_url": data.get('profile_image_url', ''),
    })


async def handle_list_recent_tweets(arguments: dict) -> str:
    """List the authenticated user's recent tweets with metrics."""
    headers = _get_bearer_headers()
    user_id = _get_user_id()
    limit = min(arguments.get('limit', 10), 100)

    resp = requests.get(
        f"{TWITTER_API_BASE}/users/{user_id}/tweets",
        params={
            "tweet.fields": "public_metrics,created_at",
            "max_results": limit,
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    tweets = []
    for tweet in result.get('data', []):
        metrics = tweet.get('public_metrics', {})
        tweets.append({
            'id': tweet.get('id'),
            'text': tweet.get('text', '')[:280],
            'created_at': tweet.get('created_at', ''),
            'likes': metrics.get('like_count', 0),
            'retweets': metrics.get('retweet_count', 0),
            'replies': metrics.get('reply_count', 0),
            'impressions': metrics.get('impression_count', 0),
        })

    return json.dumps({"tweets": tweets, "count": len(tweets)})


async def handle_search_mentions(arguments: dict) -> str:
    """Search for recent mentions of the authenticated user."""
    headers = _get_bearer_headers()
    user_id = _get_user_id()
    limit = min(arguments.get('limit', 10), 100)

    resp = requests.get(
        f"{TWITTER_API_BASE}/users/{user_id}/mentions",
        params={
            "tweet.fields": "public_metrics,created_at,author_id",
            "max_results": limit,
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    mentions = []
    for tweet in result.get('data', []):
        metrics = tweet.get('public_metrics', {})
        mentions.append({
            'id': tweet.get('id'),
            'text': tweet.get('text', '')[:280],
            'author_id': tweet.get('author_id', ''),
            'created_at': tweet.get('created_at', ''),
            'likes': metrics.get('like_count', 0),
            'retweets': metrics.get('retweet_count', 0),
            'replies': metrics.get('reply_count', 0),
        })

    return json.dumps({"mentions": mentions, "count": len(mentions)})


async def handle_reply_to_tweet(arguments: dict) -> str:
    """Reply to a specific tweet."""
    tweet_id = arguments['tweet_id']
    text = arguments['text']
    if len(text) > 280:
        return json.dumps({"error": f"Reply exceeds 280 characters ({len(text)} chars)"})

    auth = _get_oauth1()
    resp = requests.post(
        f"{TWITTER_API_BASE}/tweets",
        json={
            "text": text,
            "reply": {"in_reply_to_tweet_id": tweet_id},
        },
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    reply_id = result.get('data', {}).get('id', '')
    return json.dumps({"status": "replied", "reply_id": reply_id, "in_reply_to": tweet_id})


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "post_tweet": handle_post_tweet,
        "get_twitter_profile": handle_get_twitter_profile,
        "list_recent_tweets": handle_list_recent_tweets,
        "search_mentions": handle_search_mentions,
        "reply_to_tweet": handle_reply_to_tweet,
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
