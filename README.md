# mymind-api

Unofficial API client, CLI, and MCP server for [mymind](https://mymind.com).

mymind has no public API. This reverse-engineers the internal web app endpoints and handles authentication automatically via headless browser.

## Install

```bash
pip install mymind-api
playwright install chromium
```

## Login (one time)

```bash
mymind login
```

Enter your mymind email and password. Tokens are extracted automatically and refreshed when they expire.

## CLI

```bash
mymind list                              # list all cards
mymind search "AI"                       # search cards
mymind note "# My idea" -t "Title" --tags "startup,ai"
mymind save "https://example.com" --tags "reading"
mymind delete <card-id>
mymind tag <card-id> "new-tag"
```

## Python

```python
from mymind import MyMind

mind = MyMind()  # uses saved credentials
# or: mind = MyMind("you@email.com", "password")

cards = mind.get_all_cards()
results = mind.search("startup")
mind.create_note("# Hello", title="Note", tags=["idea"])
mind.save_url("https://example.com", tags=["reading"])
mind.add_tag(card_id, "important")
mind.delete_card(card_id)
```

Tokens auto-refresh on expiry — no manual intervention needed.

## MCP Server (for Claude, Cursor, etc.)

Run standalone:

```bash
mymind-mcp
```

Or add to Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
    "mcpServers": {
        "mymind": {
            "command": "mymind-mcp"
        }
    }
}
```

### Available tools

| Tool | Description |
|------|-------------|
| `search_mymind` | Search cards by title, description, or tags |
| `list_recent_cards` | List most recent cards |
| `create_note` | Create a note with markdown content |
| `save_url` | Save a URL/bookmark |
| `add_tag` | Tag an existing card |
| `delete_card` | Delete a card |

## How it works

1. On `mymind login`, Playwright launches a headless Chromium browser
2. Logs into mymind with your email/password
3. Intercepts the `cards.json` request to extract session tokens
4. Saves credentials + tokens to `~/.mymind/config.json` (mode 600)
5. On any API call, if tokens have expired (302/401/403), automatically re-logs in and retries

## Disclaimer

This is an unofficial project. mymind does not provide a public API — this may break if they change their internal endpoints. Use at your own risk.
