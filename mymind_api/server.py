"""
mymind MCP Server — exposes your mymind as tools for Claude and other LLMs.

Install: pip install mymind-api
Run:     mymind-mcp

Or add to Claude Desktop config:
{
    "mcpServers": {
        "mymind": {
            "command": "mymind-mcp"
        }
    }
}
"""

from fastmcp import FastMCP
from mymind_api.client import MyMind, Card
from typing import Optional, List

mcp = FastMCP("mymind")

_client = None


def _get_client() -> MyMind:
    global _client
    if _client is None:
        _client = MyMind()
    return _client


def _card_to_dict(card: Card) -> dict:
    return {
        "slug": card.slug,
        "title": card.title,
        "description": card.description,
        "domain": card.domain,
        "source_url": card.source_url,
        "tags": card.tags,
        "created": card.created,
        "modified": card.modified,
        "type": card.card_type,
        "content": card.prose_markdown,
        "notes": card.note_markdown,
    }


@mcp.tool
def search_mymind(query: str) -> list:
    """Search your mymind cards by title, description, or tags.

    Args:
        query: Search term to match against card titles, descriptions, and tags.

    Returns:
        List of matching cards with their content and metadata.
    """
    mind = _get_client()
    cards = mind.search(query)
    return [_card_to_dict(c) for c in cards]


@mcp.tool
def list_recent_cards(limit: int = 20) -> list:
    """List your most recent mymind cards.

    Args:
        limit: Max number of cards to return (default 20).

    Returns:
        List of recent cards sorted newest-first.
    """
    mind = _get_client()
    cards = mind.get_all_cards()[:limit]
    return [_card_to_dict(c) for c in cards]


@mcp.tool
def create_note(content: str, title: str = "", tags: Optional[List[str]] = None) -> dict:
    """Create a new note in mymind.

    Args:
        content: Markdown content for the note body.
        title: Optional title for the note.
        tags: Optional list of tags to attach (e.g. ["idea", "startup"]).

    Returns:
        Created card metadata including id and type.
    """
    mind = _get_client()
    return mind.create_note(content, title=title, tags=tags)


@mcp.tool
def save_url(url: str, tags: Optional[List[str]] = None) -> dict:
    """Save a URL/bookmark to mymind.

    Args:
        url: The URL to save. mymind will extract title, description, and image.
        tags: Optional list of tags to attach.

    Returns:
        Created card metadata including id and type.
    """
    mind = _get_client()
    return mind.save_url(url, tags=tags)


@mcp.tool
def add_tag(card_id: str, tag_name: str) -> str:
    """Add a tag to an existing mymind card.

    Args:
        card_id: The slug/id of the card to tag.
        tag_name: The tag name to add.

    Returns:
        Confirmation message.
    """
    mind = _get_client()
    mind.add_tag(card_id, tag_name)
    return f"Tagged '{card_id}' with '{tag_name}'"


@mcp.tool
def delete_card(card_id: str) -> str:
    """Delete a card from mymind.

    Args:
        card_id: The slug/id of the card to delete.

    Returns:
        Confirmation message.
    """
    mind = _get_client()
    mind.delete_card(card_id)
    return f"Deleted card '{card_id}'"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
