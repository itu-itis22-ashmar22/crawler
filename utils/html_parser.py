from __future__ import annotations

import re
from html.parser import HTMLParser

from utils.url_utils import resolve_url, should_skip_url


WHITESPACE_RE = re.compile(r"\s+")
IGNORED_TAGS = {"script", "style", "noscript"}


class SimpleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_chunks: list[str] = []
        self.hrefs: list[str] = []
        self._ignored_tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in IGNORED_TAGS:
            self._ignored_tag_stack.append(normalized_tag)

        if normalized_tag == "a":
            for attr_name, attr_value in attrs:
                if attr_name.lower() == "href" and attr_value:
                    self.hrefs.append(attr_value)
                    break

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self._ignored_tag_stack and normalized_tag == self._ignored_tag_stack[-1]:
            self._ignored_tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._ignored_tag_stack:
            return
        if data.strip():
            self.text_chunks.append(data.strip())


def extract_text_and_links(html: str, base_url: str) -> tuple[str, list[str]]:
    parser = SimpleHTMLParser()
    parser.feed(html)
    parser.close()

    text = WHITESPACE_RE.sub(" ", " ".join(parser.text_chunks)).strip()

    links: list[str] = []
    seen_links: set[str] = set()
    for href in parser.hrefs:
        resolved = resolve_url(base_url, href)
        if not resolved or should_skip_url(resolved):
            continue
        if resolved in seen_links:
            continue
        seen_links.add(resolved)
        links.append(resolved)

    return text, links
