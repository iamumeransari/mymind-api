"""
mymind MCP Server — full mymind management for Claude Code.

Install: pip install mymind-api
Run:     mymind-mcp
"""

from fastmcp import FastMCP
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

    Always use this tool to find cards. Provide any combination of filters.

    Args:
        query: Text search across titles, descriptions, and content (e.g. "AI", "startup ideas").
        tag: Filter by tag name (e.g. "design", "AI", "motivation"). Case-insensitive.
        domain: Filter by source domain (e.g. "x.com", "youtube.com", "github.com").
        card_type: Filter by type (e.g. "XPost", "Note", "WebPage", "Video", "Image", "Content").
        limit: Max results (default 50).
    """
    mind = _get_client()

    # If we have tag/domain/type filters, use client-side filtering (which also supports text)
    if tag or domain or card_type:
        cards = mind.filter_cards(tag=tag, domain=domain, card_type=card_type, text=query, limit=limit)
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

    # Text-only search: use fast server-side search, then hydrate with card details
    if query:
        results = mind.search(query)
        match_ids = {m["id"] for m in results.get("matches", [])}
        cards = mind.get_all_cards()
        matched = [c for c in cards if c.slug in match_ids][:limit]
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
            for c in matched
        ]

    # No filters at all — return recent cards
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
    """Get full details of a specific card including all metadata.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    return mind.get_object(card_id)


@mcp.tool
def get_card_content(card_id: str) -> dict:
    """Get the full content of a card — title, description, prose, notes, tags, source.

    Args:
        card_id: The card's ID/slug.
    """
    mind = _get_client()
    return mind.get_card_content(card_id)


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
    """List all tags in mymind, sorted by usage count.

    Args:
        limit: Max tags to return (default 50).
    """
    mind = _get_client()
    return mind.get_tags()[:limit]


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
