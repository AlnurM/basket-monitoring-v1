"""Telegram message splitting utility.

Telegram messages have a 4096 character limit. This module provides
a helper to split long report texts at newline boundaries.
"""

MAX_MESSAGE_LENGTH = 4096


def split_message(
    text: str, max_length: int = MAX_MESSAGE_LENGTH
) -> list[str]:
    """Split text into parts that fit within max_length, breaking at newlines.

    If text fits within max_length, returns [text].
    Otherwise finds the last newline before the limit and splits there.
    """
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            parts.append(remaining)
            break

        # Find last newline before the limit
        split_at = remaining.rfind("\n", 0, max_length)
        if split_at == -1:
            # No newline found; force split at max_length
            split_at = max_length

        parts.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    return parts
