from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "MiniCrawler/1.0"


def _decode_body(raw_body: bytes, content_type: str, charset: str | None) -> str:
    selected_charset = charset
    if not selected_charset and "charset=" in content_type.lower():
        selected_charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip()
    if not selected_charset:
        selected_charset = "utf-8"
    try:
        return raw_body.decode(selected_charset, errors="replace")
    except LookupError:
        return raw_body.decode("utf-8", errors="replace")


def fetch_html(url: str, timeout: int = 10) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = response.getcode() or 0
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset()
            raw_body = response.read()
            html_text = _decode_body(raw_body, content_type, charset)
            return status_code, content_type, html_text
    except HTTPError as error:
        content_type = error.headers.get("Content-Type", "")
        charset = error.headers.get_content_charset()
        raw_body = error.read()
        html_text = _decode_body(raw_body, content_type, charset)
        return error.code, content_type, html_text
    except (OSError, URLError, ValueError):
        return 0, "", ""
