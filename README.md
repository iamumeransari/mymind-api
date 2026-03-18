# mymind-api

Unofficial Python API client, CLI, and MCP server for [mymind](https://mymind.com).

Your mymind is full of things that define how you think — the articles that shaped your perspective, the tweets that resonated, the snippets you highlighted, the ideas you saved at 2am. It's the richest, most personal context you have. When you're working with Claude Code or Obsidian, that context is what makes AI actually useful to *you* specifically, not just generically.

mymind doesn't have a public API. So this project reverse-engineers their internal endpoints — giving you a Python client, a CLI, and an MCP server so Claude Code (or any AI tool) can search, read, and manage your mymind.

## Install

```bash
pip install mymind-api
```

## Login

```bash
mymind login
```

This opens mymind in your default browser. Sign in with Google or Apple as usual.

Once you're signed in and can see your cards:

1. Open DevTools (`Cmd+Option+I` on Mac, `F12` on Windows)
2. Go to the **Network** tab
3. In the Network tab's filter bar at the top, type **`cards`** — this filters out noise so you can spot the right request
4. Now refresh the page (`Cmd+R` / `Ctrl+R`) — a request called `cards` will appear in the list
5. Right-click the `cards` request → **Copy as cURL**
6. Go back to your terminal where `mymind login` is waiting, paste it, and wait 2 seconds

> **Note:** The `cards` request only fires on page load, which is why you need to set up the filter *before* refreshing. If you refresh first, you'll miss it.

> You can also click the `cards` request, copy the raw request headers, and paste those instead — the parser extracts tokens from either format.

Tokens are stored in your **system keychain** (macOS Keychain / Windows Credential Locker), never in plaintext files. If they expire, you'll be prompted to re-authenticate.

## Python API

```python
from mymind_api import MyMind

mind = MyMind()

# Cards
cards = mind.get_all_cards()
card = mind.get_card_content(card_id)
obj = mind.get_object(card_id)

# Search & filter
results = mind.search("startup ideas")
mind.filter_cards(tag="design", domain="x.com")
mind.filter_cards(card_type="Snippet", text="quote")

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

### MCP tools

| Tool | Description |
|------|-------------|
| `search_mymind` | Search and filter cards by text, tag, domain, and/or content type |
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
