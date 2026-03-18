"""
mymind — unofficial Python API client.

Zero setup: just provide email + password. Tokens are extracted
automatically via headless browser and refreshed on expiry.

Usage:
    from mymind import MyMind
    mind = MyMind("you@email.com", "password")
    cards = mind.get_all_cards()
    mind.create_note("# Hello", title="My Note", tags=["idea"])
    mind.save_url("https://example.com")
"""

import json
import os
import re
import logging
import requests
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

log = logging.getLogger("mymind")

CONFIG_DIR = Path.home() / ".mymind"
CONFIG_PATH = CONFIG_DIR / "config.json"
BASE_URL = "https://access.mymind.com"


# ── Data ─────────────────────────────────────────────────


@dataclass
class Card:
    slug: str
    title: str
    description: str
    domain: str
    source_url: str
    tags: List[str]
    created: str
    modified: str
    card_type: str = ""
    prose_markdown: str = ""
    note_markdown: str = ""
    raw: dict = field(default_factory=dict, repr=False)


# ── Token management ────────────────────────────────────


def _extract_tokens(email: str, password: str) -> dict:
    """Log into mymind via headless browser and extract session tokens."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import subprocess, sys
        log.info("Installing playwright...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.sync_api import sync_playwright

    captured = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        def on_request(request):
            if "cards.json" in request.url:
                headers = request.headers
                captured["authenticity_token"] = headers.get(
                    "x-authenticity-token", ""
                )
                for part in headers.get("cookie", "").split(";"):
                    part = part.strip()
                    if part.startswith("_jwt="):
                        captured["jwt"] = part[5:]
                    elif part.startswith("_cid="):
                        captured["cid"] = part[5:]

        page = context.new_page()
        page.on("request", on_request)

        page.goto("https://access.mymind.com/signin")
        page.wait_for_load_state("networkidle")

        page.fill('input[type="email"], input[name="email"]', email)
        page.fill('input[type="password"], input[name="password"]', password)
        page.click('button[type="submit"]')

        try:
            page.wait_for_url("**/everything**", timeout=15000)
            page.wait_for_timeout(3000)
        except Exception:
            page.wait_for_timeout(5000)

        browser.close()

    required = ("jwt", "cid", "authenticity_token")
    if not all(k in captured for k in required):
        missing = [k for k in required if k not in captured]
        raise RuntimeError(
            f"Login failed — could not capture: {missing}. "
            "Check your email/password."
        )

    return captured


def _save_config(email: str, password: str, tokens: dict):
    """Save credentials + tokens to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "email": email,
        "password": password,
        "jwt": tokens["jwt"],
        "cid": tokens["cid"],
        "authenticity_token": tokens["authenticity_token"],
    }
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
    os.chmod(CONFIG_PATH, 0o600)


def _load_config() -> Optional[dict]:
    """Load saved config, or None if missing."""
    if not CONFIG_PATH.exists():
        return None
    return json.loads(CONFIG_PATH.read_text())


# ── Client ───────────────────────────────────────────────


class MyMind:
    """mymind API client with automatic token management.

    Tokens are extracted on first use and auto-refreshed when they expire.
    """

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """Initialize the client.

        Args:
            email: mymind account email. If omitted, loads from ~/.mymind/config.json
            password: mymind account password. If omitted, loads from config.
        """
        config = _load_config()

        if email and password:
            self._email = email
            self._password = password
        elif config and "email" in config:
            self._email = config["email"]
            self._password = config["password"]
        else:
            raise ValueError(
                "Provide email and password, or run: mymind login"
            )

        # Try loading cached tokens
        if config and config.get("jwt"):
            self._jwt = config["jwt"]
            self._cid = config["cid"]
            self._authenticity_token = config["authenticity_token"]
        else:
            self._refresh_tokens()

    def _refresh_tokens(self):
        """Re-login and extract fresh tokens."""
        log.info("Refreshing mymind tokens...")
        tokens = _extract_tokens(self._email, self._password)
        self._jwt = tokens["jwt"]
        self._cid = tokens["cid"]
        self._authenticity_token = tokens["authenticity_token"]
        _save_config(self._email, self._password, tokens)
        log.info("Tokens refreshed and saved.")

    def _headers(self) -> dict:
        return {
            "x-authenticity-token": self._authenticity_token,
            "cookie": f"_cid={self._cid}; _jwt={self._jwt}",
        }

    def _headers_json(self) -> dict:
        h = self._headers()
        h["Content-Type"] = "application/json"
        return h

    def _request(self, method: str, path: str, retry: bool = True, **kwargs) -> requests.Response:
        """Make an authenticated request. Auto-refreshes tokens on auth failure."""
        url = f"{BASE_URL}{path}"
        headers = kwargs.pop("headers", None) or self._headers()
        resp = requests.request(
            method, url, headers=headers, allow_redirects=False, **kwargs
        )

        if resp.status_code in (302, 401, 403) and retry:
            log.info("Got %d, refreshing tokens...", resp.status_code)
            self._refresh_tokens()
            # Rebuild headers with new tokens
            if "Content-Type" in headers:
                new_headers = self._headers_json()
            else:
                new_headers = self._headers()
            return self._request(method, path, retry=False, headers=new_headers, **kwargs)

        if resp.status_code in (302, 401, 403):
            raise PermissionError(
                "Auth failed even after token refresh. Check email/password."
            )
        resp.raise_for_status()
        return resp

    # ── Read ─────────────────────────────────────────────

    def get_all_cards(self) -> List[Card]:
        """Fetch all cards, sorted newest-first."""
        resp = self._request("GET", "/cards.json")
        data = resp.json()
        cards = [_parse_card(slug, raw) for slug, raw in data.items()]
        cards.sort(key=lambda c: c.modified, reverse=True)
        return cards

    def search(self, query: str) -> List[Card]:
        """Search cards by title, description, or tag name."""
        q = query.lower()
        return [
            c for c in self.get_all_cards()
            if q in (c.title or "").lower()
            or q in (c.description or "").lower()
            or any(q in t.lower() for t in c.tags)
        ]

    # ── Create ───────────────────────────────────────────

    def create_note(self, content: str, title: str = "", tags: Optional[List[str]] = None) -> dict:
        """Create a note with markdown content."""
        payload = {
            "title": title,
            "prose": {
                "type": "doc",
                "content": _markdown_to_prose(content),
            },
            "type": "Note",
        }
        resp = self._request("POST", "/objects", headers=self._headers_json(), json=payload)
        result = resp.json()

        if tags:
            card_id = result.get("id", "")
            for tag in tags:
                self.add_tag(card_id, tag)
        return result

    def save_url(self, url: str, tags: Optional[List[str]] = None) -> dict:
        """Save a URL/bookmark."""
        payload = {"url": url, "type": "WebPage"}
        resp = self._request("POST", "/objects", headers=self._headers_json(), json=payload)
        result = resp.json()

        if tags:
            card_id = result.get("id", "")
            for tag in tags:
                self.add_tag(card_id, tag)
        return result

    # ── Update ───────────────────────────────────────────

    def add_tag(self, slug: str, tag_name: str) -> None:
        """Add a tag to a card."""
        self._request(
            "POST", f"/objects/{slug}/tags",
            headers=self._headers_json(),
            json={"name": tag_name},
        )

    # ── Delete ───────────────────────────────────────────

    def delete_card(self, slug: str) -> None:
        """Delete a card by slug/id."""
        self._request("DELETE", f"/objects/{slug}")

    # ── Utilities ────────────────────────────────────────

    def test_connection(self) -> bool:
        """Test if connection works (refreshes tokens if needed)."""
        try:
            self._request("GET", "/cards.json")
            return True
        except Exception:
            return False


# ── Helpers ──────────────────────────────────────────────


def _parse_card(slug: str, raw: dict) -> Card:
    tags = [t["name"] for t in raw.get("tags", []) if "name" in t]
    source = raw.get("source", {})

    prose_md = ""
    if raw.get("prose", {}).get("content"):
        prose_md = _prose_to_markdown(raw["prose"]["content"])

    note_md = ""
    note = raw.get("note")
    if note and note.get("prose", {}).get("content"):
        note_md = _prose_to_markdown(note["prose"]["content"])

    return Card(
        slug=slug,
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        domain=raw.get("domain", ""),
        source_url=source.get("url", ""),
        tags=tags,
        created=raw.get("created", ""),
        modified=raw.get("modified", ""),
        card_type=raw.get("type", ""),
        prose_markdown=prose_md,
        note_markdown=note_md,
        raw=raw,
    )


def _prose_to_markdown(content: list) -> str:
    parts = []
    for node in content:
        if not node:
            continue
        t = node.get("type", "")

        if t == "heading":
            level = node.get("attrs", {}).get("level", 1)
            text = "".join(c.get("text", "") for c in node.get("content", []))
            parts.append(f"{'#' * level} {text}\n")
        elif t == "paragraph":
            if not node.get("content"):
                parts.append("\n")
            else:
                text = _inline_to_markdown(node["content"])
                parts.append(f"{text}\n")
        elif t == "orderedList":
            idx = node.get("attrs", {}).get("start", 1)
            for item in node.get("content", []):
                item_text = ""
                for c in item.get("content", []):
                    if c.get("type") == "paragraph":
                        item_text += "".join(x.get("text", "") for x in c.get("content", []))
                parts.append(f"{idx}. {item_text}\n")
                idx += 1
        elif t == "taskList":
            for item in node.get("content", []):
                checked = item.get("attrs", {}).get("checked", False)
                mark = "x" if checked else " "
                item_text = ""
                for c in item.get("content", []):
                    if c.get("type") == "paragraph":
                        item_text += "".join(x.get("text", "") for x in c.get("content", []))
                parts.append(f"- [{mark}] {item_text}\n")
        elif t == "codeBlock":
            lang = node.get("attrs", {}).get("language", "")
            code = "".join(c.get("text", "") for c in node.get("content", []))
            parts.append(f"```{lang}\n{code}\n```\n")
        elif t == "horizontalRule":
            parts.append("---\n")

    return "\n".join(parts)


def _inline_to_markdown(content: list) -> str:
    parts = []
    for c in content:
        if not c:
            continue
        text = c.get("text", "")
        for mark in c.get("marks", []):
            mt = mark.get("type", "")
            if mt == "bold":
                text = f"**{text}**"
            elif mt == "italic":
                text = f"*{text}*"
            elif mt == "strike":
                text = f"~~{text}~~"
            elif mt == "code":
                text = f"`{text}`"
            elif mt == "highlight":
                text = f"=={text}=="
        parts.append(text)
    return "".join(parts)


def _markdown_to_prose(markdown: str) -> list:
    lines = markdown.split("\n")
    content = []
    in_code = False
    code_buf = ""
    code_lang = ""

    for line in lines:
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                code_buf = ""
            else:
                content.append({
                    "type": "codeBlock",
                    "attrs": {"language": code_lang},
                    "content": [{"type": "text", "text": code_buf.rstrip("\n")}],
                })
                in_code = False
            continue
        if in_code:
            code_buf += line + "\n"
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading:
            content.append({
                "type": "heading",
                "attrs": {"level": len(heading.group(1))},
                "content": [{"type": "text", "text": heading.group(2)}],
            })
            continue

        task = re.match(r"^- \[(x| )\] (.+)", line)
        if task:
            content.append({
                "type": "taskItem",
                "attrs": {"checked": task.group(1) == "x"},
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": task.group(2)}]}],
            })
            continue

        if re.match(r"^-{3,}$", line):
            content.append({"type": "horizontalRule"})
            continue

        if line.strip():
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line}],
            })
        else:
            content.append({"type": "paragraph"})

    return content


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="mymind",
        description="Unofficial mymind CLI & API",
    )
    sub = parser.add_subparsers(dest="command")

    login_p = sub.add_parser("login", help="Save your mymind credentials")
    login_p.add_argument("--email", help="mymind email")
    login_p.add_argument("--password", help="mymind password")

    sub.add_parser("test", help="Test your connection")
    sub.add_parser("list", help="List all cards")

    search_p = sub.add_parser("search", help="Search cards")
    search_p.add_argument("query", help="Search query")

    note_p = sub.add_parser("note", help="Create a note")
    note_p.add_argument("content", help="Note content (markdown)")
    note_p.add_argument("-t", "--title", default="", help="Note title")
    note_p.add_argument("--tags", default="", help="Comma-separated tags")

    url_p = sub.add_parser("save", help="Save a URL")
    url_p.add_argument("url", help="URL to save")
    url_p.add_argument("--tags", default="", help="Comma-separated tags")

    del_p = sub.add_parser("delete", help="Delete a card")
    del_p.add_argument("slug", help="Card slug/id")

    tag_p = sub.add_parser("tag", help="Add a tag to a card")
    tag_p.add_argument("slug", help="Card slug/id")
    tag_p.add_argument("tag_name", help="Tag to add")

    args = parser.parse_args()

    if args.command == "login":
        email = args.email or input("mymind email: ").strip()
        password = args.password
        if not password:
            import getpass
            password = getpass.getpass("mymind password: ")

        print("Logging in...")
        tokens = _extract_tokens(email, password)
        _save_config(email, password, tokens)
        print("Logged in and tokens saved to ~/.mymind/config.json")

    elif args.command == "test":
        mind = MyMind()
        if mind.test_connection():
            print("Connected to mymind!")
        else:
            print("Connection failed. Run: mymind login")

    elif args.command == "list":
        mind = MyMind()
        cards = mind.get_all_cards()
        for c in cards:
            tags_str = f" [{', '.join(c.tags)}]" if c.tags else ""
            print(f"  {c.slug}  {c.title or '(untitled)'}{tags_str}")
        print(f"\n{len(cards)} cards total")

    elif args.command == "search":
        mind = MyMind()
        results = mind.search(args.query)
        for c in results:
            print(f"  {c.slug}  {c.title or '(untitled)'}")
        print(f"\n{len(results)} results")

    elif args.command == "note":
        mind = MyMind()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        result = mind.create_note(args.content, title=args.title, tags=tags)
        print(f"Created: {result}")

    elif args.command == "save":
        mind = MyMind()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        result = mind.save_url(args.url, tags=tags)
        print(f"Saved: {result}")

    elif args.command == "delete":
        mind = MyMind()
        mind.delete_card(args.slug)
        print("Deleted.")

    elif args.command == "tag":
        mind = MyMind()
        mind.add_tag(args.slug, args.tag_name)
        print(f"Tagged '{args.slug}' with '{args.tag_name}'")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
