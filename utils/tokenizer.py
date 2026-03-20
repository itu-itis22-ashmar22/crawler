from __future__ import annotations

import re
from collections import Counter


TOKEN_SPLIT_RE = re.compile(r"[^0-9a-zA-Z]+")
TOKEN_CLEAN_RE = re.compile(r"[^0-9a-z]+")


def normalize_word(word: str) -> str:
    cleaned = TOKEN_CLEAN_RE.sub("", word.strip().lower())
    return cleaned


def tokenize_text(text: str) -> list[str]:
    tokens: list[str] = []
    for part in TOKEN_SPLIT_RE.split(text.lower()):
        token = normalize_word(part)
        if not token:
            continue
        if len(token) < 2:
            continue
        tokens.append(token)
    return tokens


def count_words(text: str) -> dict[str, int]:
    return dict(Counter(tokenize_text(text)))
