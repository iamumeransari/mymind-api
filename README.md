# mymind-api

Unofficial Python API client, CLI, and MCP server for [mymind](https://mymind.com).

mymind has no public API. This reverse-engineers the internal web app endpoints so you can manage your cards, tags, and spaces programmatically.

## Install

```bash
pip install mymind-api
```

## Login

```bash
mymind login
```

This opens mymind in your default browser. Sign in with Google or Apple, then:

1. Open DevTools → Network tab (`Cmd+Option+I`)
2. Refresh the page
3. Click the `cards` request
4. Copy the request headers and paste into the terminal

Tokens are stored in your **system keychain** (macOS Keychain / Windows Credential Locker). If they expire, you'll be prompted to re-authenticate.

## Python API

```python
from mymind_api import MyMind

mind = MyMind()

# Cards
cards = mind.get_all_cards()
card = mind.get_card_content(card_id)
obj = mind.get_object(card_id)
results = mind.search("startup ideas")

# Create
mind.create_note("# Hello", title="My Note", tags=["idea"])
mind.save_url("https://example.com", tags=["reading"])

# Update
mind.update_object(card_id, {"title": "New Title"})
mind.delete_card(card_id)

# Tags
mind.get_tags()                       # all tags
mind.get_object_tags(card_id)         # tags on a card
mind.add_tag(card_id, "important")
mind.remove_tag(card_id, "old-tag")

# Spaces
mind.get_spaces()
mind.create_space("Research")
mind.create_smart_space("AI Articles", ["ai", "type:webpage"])
mind.delete_space(space_id)
```

## CLI

```bash
mymind list                              # list all cards
mymind search "AI"                       # search cards
mymind note "# My idea" -t "Title" --tags "startup,ai"
mymind save "https://example.com" --tags "reading"
mymind delete <card-id>
mymind tag <card-id> "new-tag"
mymind test                              # test connection
mymind logout                            # remove tokens
```

## MCP Server (Claude Code, Claude Desktop, Cursor, etc.)

```bash
mymind-mcp
```

Add to Claude Code:

```bash
claude mcp add --transport stdio mymind -- mymind-mcp
```

Or Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
    "mcpServers": {
        "mymind": {
            "command": "mymind-mcp"
        }
    }
}
```

### 16 MCP tools

| Tool | Description |
|------|-------------|
| `search_mymind` | Full-text search across all cards |
| `list_recent_cards` | List most recently saved cards |
| `get_card` | Get full card metadata |
| `get_card_content` | Get card content (prose, notes, tags, source) |
| `create_note` | Create a note with markdown content |
| `save_url` | Save a URL/bookmark |
| `update_card` | Update a card's title |
| `delete_card` | Delete a card |
| `list_tags` | List all tags sorted by usage |
| `get_card_tags` | Get tags on a specific card |
| `add_tag` | Add a tag to a card |
| `remove_tag` | Remove a tag from a card |
| `list_spaces` | List all spaces |
| `create_space` | Create a manual space |
| `create_smart_space` | Create a smart space with filters |
| `delete_space` | Delete a space |

## Disclaimer

This is an unofficial project. mymind does not provide a public API — this may break if they change their internal endpoints.
