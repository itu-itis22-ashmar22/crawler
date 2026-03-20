from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORAGE_ROOT = PROJECT_ROOT / "storage"
CRAWLERS_ROOT = STORAGE_ROOT / "crawlers"
LOGS_ROOT = STORAGE_ROOT / "logs"
QUEUES_ROOT = STORAGE_ROOT / "queues"
WORDS_ROOT = STORAGE_ROOT / "words"
VISITED_PATH = STORAGE_ROOT / "visited_urls.data"


def ensure_storage_layout() -> None:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    CRAWLERS_ROOT.mkdir(parents=True, exist_ok=True)
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    QUEUES_ROOT.mkdir(parents=True, exist_ok=True)
    WORDS_ROOT.mkdir(parents=True, exist_ok=True)
    VISITED_PATH.touch(exist_ok=True)


def _coerce_path(path: str | Path) -> Path:
    return Path(path)


def read_json(path: str | Path) -> dict:
    json_path = _coerce_path(path)
    if not json_path.exists():
        return {}

    try:
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def write_json(path: str | Path, data: dict) -> None:
    json_path = _coerce_path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def append_line(path: str | Path, line: str) -> None:
    target_path = _coerce_path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")


def read_lines(path: str | Path) -> list[str]:
    target_path = _coerce_path(path)
    if not target_path.exists():
        return []

    with target_path.open("r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def tail_lines(path: str | Path, n: int = 100) -> list[str]:
    if n <= 0:
        return []
    lines = read_lines(path)
    return lines[-n:]


def crawler_data_path(crawler_id: str) -> str:
    return str(CRAWLERS_ROOT / f"{crawler_id}.data.json")


def crawler_log_path(crawler_id: str) -> str:
    return str(LOGS_ROOT / f"{crawler_id}.log")


def crawler_queue_path(crawler_id: str) -> str:
    return str(QUEUES_ROOT / f"{crawler_id}.queue")


def word_file_path(word: str) -> str:
    first_char = word[:1].lower()
    bucket = first_char if first_char.isalpha() and "a" <= first_char <= "z" else "misc"
    return str(WORDS_ROOT / f"{bucket}.data")


def load_visited_urls() -> set[str]:
    ensure_storage_layout()
    return set(read_lines(VISITED_PATH))


def append_visited_url(url: str) -> None:
    append_line(VISITED_PATH, url)


def append_queue_item(crawler_id: str, depth: int, url: str) -> None:
    append_line(crawler_queue_path(crawler_id), f"{depth}\t{url}")


def rewrite_queue_file(crawler_id: str, queue_items: Iterable[tuple[int, str]]) -> None:
    queue_path = Path(crawler_queue_path(crawler_id))
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w", encoding="utf-8") as handle:
        for depth, url in queue_items:
            handle.write(f"{depth}\t{url}\n")


def append_log(crawler_id: str, message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    append_line(crawler_log_path(crawler_id), f"{timestamp} {message}")


def append_word_record(
    word: str,
    relevant_url: str,
    origin_url: str,
    depth: int,
    frequency: int,
) -> None:
    append_line(
        word_file_path(word),
        f"{word}\t{relevant_url}\t{origin_url}\t{depth}\t{frequency}",
    )


def load_crawler_records() -> list[dict]:
    ensure_storage_layout()
    records: list[dict] = []
    for data_file in CRAWLERS_ROOT.glob("*.data.json"):
        record = read_json(data_file)
        if record:
            records.append(record)

    def sort_key(record: dict) -> str:
        return str(record.get("created_at", ""))

    return sorted(records, key=sort_key, reverse=True)


def count_word_records() -> int:
    ensure_storage_layout()
    total = 0
    for bucket_file in WORDS_ROOT.glob("*.data"):
        with bucket_file.open("r", encoding="utf-8") as handle:
            total += sum(1 for line in handle if line.strip())
    return total
