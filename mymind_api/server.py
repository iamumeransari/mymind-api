"""
mymind MCP Server — full mymind management for Claude Code.

Install: pip install mymind-api
Run:     mymind-mcp
"""

import base64
from fastmcp import FastMCP
from mcp.types import ImageContent, TextContent
from mymind_api.client import MyMind
from typing import Optional, List

mcp = FastMCP("mymind")

_client = None


def _get_client() -> MyMind:
    global _client
    if _client is None:
        _client = MyMind()
    return _client


# ── Search & Browse ──────────────────────────────────────


@mcp.tool
def search_mymind(
    query: Optional[str] = None,
    tag: Optional[str] = None,
    domain: Optional[str] = None,
    card_type: Optional[str] = None,
    limit: int = 50,
) -> list:
    """Search and filter mymind cards. Combines server-side text search with client-side
    tag/domain/type filtering. All provided filters are AND-ed together.

    SEARCH STRATEGY — FOLLOW THIS EXACTLY:

    1. TAGS FIRST. Always start with tag-based search. Call `list_tags()` first
       to see what tags exist. Tags may be concatenated (e.g. "productlaunch"
       not "product launch") — check for both forms. Comma-separated tags are
       AND-ed. Avoid card_type filtering — content comes in many forms.

    2. USE SHORT VARIED QUERIES. Don't search one long phrase. Use 2-3 short
       queries with different terms: "product video", "launch video", "feature
       video" — not "product launch video announcement demo". Also search by
       tag separately from query — the tag index and text index behave
       differently and surface different cards.

    3. TITLES ARE UNRELIABLE FOR DISCOVERY. Cards saved from social posts
       often have the first line of the post as the title (e.g. "Hey folks!"),
       not a descriptive name. Tags and description are more reliable signals
       than titles for finding cards. But titles ARE useful for judging
       relevance once you have results.

    4. JUDGE RELEVANCE BY TITLE + DESCRIPTION. After collecting results, read
       each card's title and description. Only include cards that are exactly
       what the user asked for. Drop everything else — no "related" filler.

    5. NEVER PAD. If the user asks for 10 but only 4 match, return 4. Say
       "found 4 that match." Do NOT backfill with tools, studios, techniques,
       or tangentially related content to hit the number.

    6. IMAGES: mymind images are auth-protected — no embeddable URLs
       exist. Use source_url (the original tweet, article, video link)
       when linking cards in Notion, docs, etc.

    7. ALWAYS STORE CARD IDs. When writing mymind cards to Notion, Obsidian,
       or anywhere else, always include the mymind card ID (the "id" field).
       This enables direct lookups later via get_card() or get_cards_by_ids()
       instead of having to re-search by title.

    Args:
        query: Text search across titles, descriptions, and content.
        tag: Filter by tag name(s). Case-insensitive. Comma-separated for multiple
            (e.g. "startup, launch") — card must have ALL listed tags. Tags may
            be concatenated in mymind (e.g. "productlaunch" not "product launch").
        domain: Filter by source domain (e.g. "x.com", "youtube.com", "github.com").
        card_type: Filter by content type (WebPage, Image, XPost, Article,
            YouTubeVideo, InstagramReel, Video, Note, Snippet, Quotation,
            RedditPost, Product, Post, Recipe, MusicRecording,
            SoftwareApplication, Book, Movie, Document). Prefer tags over this.
        limit: Max results (default 50).
    """
    mind = _get_client()

    # Parse comma-separated tags into a list
    tags_list = None
    if tag:
        tags_list = [t.strip() for t in tag.split(",") if t.strip()]

    # If we have tag/domain/type filters, use client-side filtering (which also supports text)
    if tags_list or domain or card_type:
        cards = mind.filter_cards(tags=tags_list, domain=domain, card_type=card_type, text=query, limit=limit)
        return _format_results(cards)

    # Text-only search: use fast server-side search, then hydrate with card details
    if query:
        results = mind.search(query)
        match_ids = {m["id"] for m in results.get("matches", [])}
        cards = mind.get_all_cards()
        matched = [c for c in cards if c.slug in match_ids][:limit]
        return _format_results(matched)

    # No filters at all — return recent cards
    cards = mind.get_all_cards()[:limit]
    return _format_results(cards)


def _format_results(cards: list) -> list:
    """Format card results for search. Lightweight — no image URLs here.
    Image URLs come from get_card_content() when you're ready to use a card."""
    return [
        {
            "id": c.slug,
            "title": c.title,
            "type": c.card_type,
            "description": c.description,
            "tags": c.tags,
            "source_url": c.source_url,
            "created": c.created,
            "modified": c.modified,
        }
        for c in cards
    ]


@mcp.tool
def list_recent_cards(limit: int = 20) -> list:
    """List most recently saved/modified mymind cards.

    Args:
        limit: Max cards to return (default 20).
    """
    mind = _get_client()
    cards = mind.get_all_cards()[:limit]
    return [
        {
            "id": c.slug,
            "title": c.title,
            "type": c.card_type,
            "description": c.description,
            "tags": c.tags,
            "source_url": c.source_url,
            "created": c.created,
            "modified": c.modified,
        }
        for c in cards
    ]


# ── Card Details ─────────────────────────────────────────


@mcp.tool
def get_card(card_id: str) -> dict:
    """Get full details of a specific card by ID. Use this when you already have
    a card ID (e.g. stored in Notion or Obsidian) instead of searching by title.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    return mind.get_object(card_id)


@mcp.tool
def get_cards_by_ids(card_ids: List[str]) -> list:
    """Batch fetch multiple cards by their IDs. Use when you have card IDs stored
    in Notion, Obsidian, or elsewhere and need to pull their full details without
    searching. One call instead of N separate get_card calls.

    Args:
        card_ids: List of card ID/slugs.
    """
    mind = _get_client()
    results = []
    for card_id in card_ids:
        try:
            obj = mind.get_object(card_id)
            results.append(obj)
        except Exception:
            results.append({"card_id": card_id, "error": "not found"})
    return results


@mcp.tool
def get_card_content(card_id: str) -> dict:
    """Get the full content of a card — title, description, prose, notes, tags, source.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    return mind.get_card_content(card_id)


@mcp.tool
def get_card_image(card_id: str) -> list:
    """Get a card's image so you can see it. Returns the image inline along with card metadata.

    Works for Image cards, webpage thumbnails, and any card with a visual.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    image_bytes = mind.get_card_image(card_id)
    if not image_bytes:
        return [TextContent(type="text", text=f"Card '{card_id}' has no image.")]

    obj = mind.get_object(card_id)
    return [
        ImageContent(
            type="image",
            data=base64.b64encode(image_bytes).decode(),
            mimeType="image/webp",
        ),
        TextContent(
            type="text",
            text=f"Title: {obj.get('title', '(untitled)')}\nTags: {', '.join(t['name'] for t in obj.get('tags', []))}"
        ),
    ]


# ── Create ───────────────────────────────────────────────


@mcp.tool
def create_note(content: str, title: str = "", tags: Optional[List[str]] = None) -> dict:
    """Create a new note in mymind.

    Args:
        content: Markdown content for the note body.
        title: Optional title.
        tags: Optional list of tags (e.g. ["idea", "startup"]).
    """
    mind = _get_client()
    return mind.create_note(content, title=title, tags=tags)


@mcp.tool
def save_url(url: str, tags: Optional[List[str]] = None) -> dict:
    """Save a URL/bookmark to mymind. mymind will extract title, description, and image.

    Args:
        url: The URL to save.
        tags: Optional list of tags.
    """
    mind = _get_client()
    return mind.save_url(url, tags=tags)


# ── Update Cards ─────────────────────────────────────────


@mcp.tool
def update_card(card_id: str, title: Optional[str] = None) -> dict:
    """Update a card's title.

    Args:
        card_id: The card's ID/slug.
        title: New title for the card.
    """
    mind = _get_client()
    updates = {}
    if title is not None:
        updates["title"] = title
    return mind.update_object(card_id, updates)


@mcp.tool
def delete_card(card_id: str) -> str:
    """Delete a card from mymind.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    mind.delete_card(card_id)
    return f"Deleted card '{card_id}'"


# ── Tags ─────────────────────────────────────────────────


@mcp.tool
def list_tags(limit: int = 50) -> list:
    """List all tags in mymind (both AI-generated and custom), sorted by usage count.

    Args:
        limit: Max tags to return (default 50).
    """
    mind = _get_client()
    return mind.get_tags()[:limit]


@mcp.tool
def list_custom_tags() -> list:
    """List only user-created (custom) tags, excluding AI-generated ones.

    Custom tags are the ones the user manually created — these are more intentional
    and useful for organizing than the noisy AI-generated tags. Use these when you
    need to understand how the user actually thinks about their content.
    """
    mind = _get_client()
    return mind.get_custom_tags()


@mcp.tool
def get_card_tags(card_id: str) -> list:
    """Get all tags on a specific card.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    return mind.get_object_tags(card_id)


@mcp.tool
def add_tag(card_id: str, tag_name: str) -> str:
    """Add a tag to a card.

    Args:
        card_id: The card's ID/slug.
        tag_name: Tag name to add.
    """
    mind = _get_client()
    mind.add_tag(card_id, tag_name)
    return f"Added tag '{tag_name}' to card '{card_id}'"


@mcp.tool
def remove_tag(card_id: str, tag_name: str) -> str:
    """Remove a tag from a card.

    Args:
        card_id: The card's ID/slug.
        tag_name: Tag name to remove.
    """
    mind = _get_client()
    mind.remove_tag(card_id, tag_name)
    return f"Removed tag '{tag_name}' from card '{card_id}'"


# ── Spaces ───────────────────────────────────────────────


@mcp.tool
def list_spaces() -> list:
    """List all spaces (collections) in mymind."""
    mind = _get_client()
    return mind.get_spaces()


@mcp.tool
def get_space_cards(space_id: str) -> list:
    """Get all cards in a specific space.

    Args:
        space_id: The space's ID (get this from list_spaces).
    """
    mind = _get_client()
    return mind.get_space_cards(space_id)


@mcp.tool
def create_space(name: str, color: str = "#fdf06f") -> dict:
    """Create a new space (manual collection).

    Args:
        name: Space name.
        color: Hex color (default yellow).
    """
    mind = _get_client()
    return mind.create_space(name, color=color)


@mcp.tool
def create_smart_space(name: str, filters: List[str], color: str = "#fdf06f") -> dict:
    """Create a smart space with auto-populating filters.

    Filters use mymind's query syntax:
    - Text search: "design" or "AI tools"
    - Type filter: "type:webpage", "type:image", "type:video", "type:note"
    - Combine with ||: "design || branding"
    - Multiple filters are AND-ed together

    Args:
        name: Space name.
        filters: List of filter strings (e.g. ["design", "type:webpage"]).
        color: Hex color (default yellow).
    """
    mind = _get_client()
    return mind.create_smart_space(name, filters, color=color)


@mcp.tool
def delete_space(space_id: str) -> str:
    """Delete a space.

    Args:
        space_id: The space's ID.
    """
    mind = _get_client()
    mind.delete_space(space_id)
    return f"Deleted space '{space_id}'"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
