"""Utility functions for message formatting and splitting."""

import re
from typing import Iterator


def split_message(text: str, max_length: int = 4000) -> list[str]:
    """Split long messages for Telegram's 4096 char limit.

    Strategy:
    1. Try to split on paragraph boundaries (double newline)
    2. Fall back to line boundaries
    3. Last resort: split mid-text

    Args:
        text: The text to split.
        max_length: Maximum length per chunk (default 4000 for safety margin).

    Returns:
        List of message chunks.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Find best split point
        split_at = max_length

        # Try paragraph boundary first
        para_match = remaining[:max_length].rfind("\n\n")
        if para_match > max_length // 2:
            split_at = para_match + 2
        else:
            # Try line boundary
            line_match = remaining[:max_length].rfind("\n")
            if line_match > max_length // 2:
                split_at = line_match + 1
            else:
                # Try word boundary
                word_match = remaining[:max_length].rfind(" ")
                if word_match > max_length // 2:
                    split_at = word_match + 1

        chunk = remaining[:split_at].rstrip()
        chunks.append(chunk)
        remaining = remaining[split_at:].lstrip()

    return chunks


def format_chunks_with_markers(chunks: list[str]) -> list[str]:
    """Add continuation markers to split message chunks.

    Args:
        chunks: List of message chunks.

    Returns:
        Chunks with [1/N], [2/N], etc. markers if more than one chunk.
    """
    if len(chunks) <= 1:
        return chunks

    total = len(chunks)
    return [f"{chunk}\n\n[{i+1}/{total}]" for i, chunk in enumerate(chunks)]


# Characters that need escaping in MarkdownV2
MARKDOWN_V2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2.

    Args:
        text: Text to escape.

    Returns:
        Escaped text safe for MarkdownV2 parsing.
    """
    for char in MARKDOWN_V2_SPECIAL:
        text = text.replace(char, f"\\{char}")
    return text


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_for_telegram(text: str) -> str:
    """Format Claude's markdown output for Telegram HTML mode.

    Supported HTML tags: <b>, <i>, <code>, <pre>, <u>, <s>

    Args:
        text: Markdown text from Claude.

    Returns:
        Telegram HTML-formatted text.
    """
    # First escape HTML in the raw text
    text = escape_html(text)

    # Convert markdown to HTML

    # Convert **bold** to <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Convert headers: ## Header -> <b>Header</b>
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # Convert `code` to <code>code</code>
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)

    # Convert *italic* to <i>italic</i> (single asterisks, not inside bold)
    text = re.sub(r"(?<![*<])\*([^*\n]+)\*(?![*>])", r"<i>\1</i>", text)

    # Convert ~~strikethrough~~ to <s>strikethrough</s>
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    return text


def convert_markdown_to_telegram(text: str) -> str:
    """Alias for format_for_telegram for backwards compatibility."""
    return format_for_telegram(text)


def is_safe_for_markdown(text: str) -> bool:
    """Check if text is likely safe to parse as MarkdownV2.

    Args:
        text: Text to check.

    Returns:
        True if text appears safe for markdown parsing.
    """
    # Simple heuristic: check for unbalanced special chars
    for char in "*_`":
        if text.count(char) % 2 != 0:
            return False
    return True


def truncate_for_log(text: str, max_length: int = 100) -> str:
    """Truncate text for logging purposes.

    Args:
        text: Text to truncate.
        max_length: Maximum length.

    Returns:
        Truncated text with ellipsis if needed.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
