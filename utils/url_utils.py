from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


SKIPPED_PREFIXES = ("mailto:", "javascript:", "tel:")
SKIPPED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".pdf",
    ".zip",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
)


def normalize_url(url: str) -> str:
    raw_url = url.strip()
    if not raw_url:
        return ""

    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=path,
        fragment="",
    )
    return urlunparse(normalized)


def resolve_url(base_url: str, href: str) -> str | None:
    href_value = href.strip()
    if not href_value:
        return None

    resolved = normalize_url(urljoin(base_url, href_value))
    if not resolved:
        return None
    return resolved


def is_http_url(url: str) -> bool:
    lowered = url.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def should_skip_url(url: str) -> bool:
    candidate = url.strip()
    if not candidate:
        return True

    lowered = candidate.lower()
    if lowered.startswith(SKIPPED_PREFIXES):
        return True
    if not is_http_url(lowered):
        return True

    path = urlparse(lowered).path
    return path.endswith(SKIPPED_EXTENSIONS)


def same_domain(origin_url: str, candidate_url: str) -> bool:
    origin = urlparse(normalize_url(origin_url))
    candidate = urlparse(normalize_url(candidate_url))
    return bool(origin.netloc and origin.netloc == candidate.netloc)
