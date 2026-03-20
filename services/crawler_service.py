from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime

from services.job_manager import JobManager
from utils.file_store import (
    append_log,
    append_word_record,
    crawler_queue_path,
    read_lines,
    rewrite_queue_file,
)
from utils.html_fetcher import fetch_html
from utils.html_parser import extract_text_and_links
from utils.tokenizer import count_words
from utils.url_utils import is_http_url, normalize_url


class CrawlerService:
    def __init__(self, job_manager: JobManager) -> None:
        self.job_manager = job_manager

    def create_crawler(
        self,
        origin_url: str,
        max_depth: int | str,
        hit_rate_seconds: float | str,
        max_urls_to_visit: int | str,
        queue_capacity: int | str,
    ) -> str:
        raw_origin = str(origin_url or "").strip()
        if not raw_origin:
            raise ValueError("Origin URL is required.")
        if not is_http_url(raw_origin):
            raise ValueError("Origin URL must start with http:// or https://.")

        normalized_origin = normalize_url(raw_origin)
        if not normalized_origin or not is_http_url(normalized_origin):
            raise ValueError("Origin URL is invalid after normalization.")

        validated_max_depth = _validate_int("Max depth", max_depth, minimum=0, maximum=5)
        validated_hit_rate = _validate_float(
            "Hit rate (seconds)",
            hit_rate_seconds,
            minimum=0,
            maximum=10,
        )
        validated_max_urls = _validate_int(
            "Max URLs",
            max_urls_to_visit,
            minimum=1,
            maximum=500,
        )
        validated_queue_capacity = _validate_int(
            "Queue capacity",
            queue_capacity,
            minimum=1,
            maximum=2000,
        )

        crawler_id = self._generate_crawler_id()
        now = _timestamp()
        job_data = {
            "crawler_id": crawler_id,
            "origin_url": normalized_origin,
            "max_depth": validated_max_depth,
            "hit_rate_seconds": validated_hit_rate,
            "max_urls_to_visit": validated_max_urls,
            "queue_capacity": validated_queue_capacity,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "processed_count": 0,
            "discovered_count": 0,
            "queued_count": 1,
            "throttled": False,
            "error_message": "",
            "throttle_count": 0,
            "last_throttle_at": "",
        }

        with self.job_manager.queue_lock:
            rewrite_queue_file(crawler_id, [(0, normalized_origin)])

        thread = threading.Thread(
            target=self._run_crawler,
            args=(crawler_id,),
            daemon=True,
            name=f"crawler-{crawler_id}",
        )
        self.job_manager.register_job(job_data, thread)
        thread.start()
        return crawler_id

    def get_crawler_status(self, crawler_id: str) -> dict | None:
        return self.job_manager.get_job(crawler_id)

    def list_crawlers(self) -> list[dict]:
        return self.job_manager.list_jobs()

    def _run_crawler(self, crawler_id: str) -> None:
        job_data = self.job_manager.get_job(crawler_id)
        if not job_data:
            return

        try:
            job_data["status"] = "running"
            job_data["error_message"] = ""
            self._persist_job_state(crawler_id, job_data)
            append_log(
                crawler_id,
                f"START origin={job_data['origin_url']} max_depth={job_data['max_depth']}",
            )

            runtime_queue = self._load_runtime_queue(crawler_id, job_data["origin_url"])
            queued_urls = {url for _, url in runtime_queue}

            while runtime_queue and job_data["processed_count"] < job_data["max_urls_to_visit"]:
                latest_job = self.job_manager.get_job(crawler_id)
                if latest_job and latest_job.get("status") != "running":
                    job_data = latest_job
                    break

                depth, url = runtime_queue.popleft()
                queued_urls.discard(url)
                self._persist_queue(crawler_id, runtime_queue)

                if depth > job_data["max_depth"]:
                    append_log(crawler_id, f"SKIP depth_limit depth={depth} url={url}")
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                normalized_url = normalize_url(url)
                if not normalized_url:
                    append_log(crawler_id, "SKIP invalid_normalized_url")
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                if not self.job_manager.mark_visited(normalized_url):
                    append_log(crawler_id, f"SKIP already_visited url={normalized_url}")
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                if job_data["hit_rate_seconds"] > 0:
                    time.sleep(job_data["hit_rate_seconds"])

                append_log(crawler_id, f"FETCH_START depth={depth} url={normalized_url}")
                status_code, content_type, html_text = fetch_html(normalized_url)

                if status_code == 0:
                    append_log(crawler_id, f"FETCH_FAIL url={normalized_url}")
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                if not 200 <= status_code < 300:
                    append_log(
                        crawler_id,
                        f"FETCH_NON_200 status={status_code} url={normalized_url}",
                    )
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                if "text/html" not in content_type.lower():
                    append_log(
                        crawler_id,
                        f"FETCH_SKIP_NON_HTML type={content_type or 'unknown'} url={normalized_url}",
                    )
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                if not html_text.strip():
                    append_log(crawler_id, f"FETCH_EMPTY url={normalized_url}")
                    job_data["queued_count"] = len(runtime_queue)
                    job_data["throttled"] = len(runtime_queue) >= job_data["queue_capacity"]
                    self._persist_job_state(crawler_id, job_data)
                    continue

                visible_text, child_links = extract_text_and_links(html_text, normalized_url)
                word_counts = count_words(visible_text)
                self._write_word_records(
                    normalized_url,
                    job_data["origin_url"],
                    depth,
                    word_counts,
                )

                append_log(
                    crawler_id,
                    f"INDEX words_unique={len(word_counts)} links_found={len(child_links)} url={normalized_url}",
                )

                job_data["discovered_count"] += len(child_links)
                throttled = False
                if depth + 1 <= job_data["max_depth"]:
                    throttled = self._enqueue_links(
                        crawler_id=crawler_id,
                        runtime_queue=runtime_queue,
                        queued_urls=queued_urls,
                        child_links=child_links,
                        next_depth=depth + 1,
                        queue_capacity=job_data["queue_capacity"],
                    )
                if throttled:
                    job_data["throttle_count"] += 1
                    job_data["last_throttle_at"] = _timestamp()

                job_data["processed_count"] += 1
                job_data["queued_count"] = len(runtime_queue)
                job_data["throttled"] = throttled or len(runtime_queue) >= job_data["queue_capacity"]
                self._persist_job_state(crawler_id, job_data)
                self._persist_queue(crawler_id, runtime_queue)

            final_job = self.job_manager.get_job(crawler_id) or job_data
            if final_job.get("status") == "running":
                final_job["status"] = "completed"
                final_job["queued_count"] = len(runtime_queue) if "runtime_queue" in locals() else 0
                final_job["throttled"] = False
                self._persist_job_state(crawler_id, final_job)
                append_log(
                    crawler_id,
                    f"COMPLETE processed={final_job.get('processed_count', 0)}",
                )
        except Exception as error:  # noqa: BLE001
            failed_job = self.job_manager.get_job(crawler_id) or job_data
            failed_job["status"] = "failed"
            failed_job["error_message"] = str(error)
            failed_job["queued_count"] = len(runtime_queue) if "runtime_queue" in locals() else 0
            failed_job["throttled"] = False
            self._persist_job_state(crawler_id, failed_job)
            append_log(crawler_id, f"FAILED error={error}")

    def _load_runtime_queue(self, crawler_id: str, origin_url: str) -> deque[tuple[int, str]]:
        queue_items: deque[tuple[int, str]] = deque()
        for line in read_lines(crawler_queue_path(crawler_id)):
            try:
                depth_text, url = line.split("\t", 1)
                queue_items.append((int(depth_text), url))
            except ValueError:
                continue

        if queue_items:
            return queue_items
        return deque([(0, origin_url)])

    def _persist_job_state(self, crawler_id: str, job_data: dict) -> None:
        job_data["updated_at"] = _timestamp()
        self.job_manager.update_job(crawler_id, job_data)

    def _persist_queue(self, crawler_id: str, runtime_queue: deque[tuple[int, str]]) -> None:
        with self.job_manager.queue_lock:
            rewrite_queue_file(crawler_id, list(runtime_queue))

    def _enqueue_links(
        self,
        crawler_id: str,
        runtime_queue: deque[tuple[int, str]],
        queued_urls: set[str],
        child_links: list[str],
        next_depth: int,
        queue_capacity: int,
    ) -> bool:
        throttled = False
        for child_url in child_links:
            normalized_child = normalize_url(child_url)
            if not normalized_child or normalized_child in queued_urls:
                continue
            with self.job_manager.visited_lock:
                if normalized_child in self.job_manager.visited_urls:
                    continue
            if len(runtime_queue) >= queue_capacity:
                throttled = True
                append_log(
                    crawler_id,
                    f"THROTTLED queue_capacity={queue_capacity} queued={len(runtime_queue)}",
                )
                break
            runtime_queue.append((next_depth, normalized_child))
            queued_urls.add(normalized_child)
        return throttled

    def _write_word_records(
        self,
        relevant_url: str,
        origin_url: str,
        depth: int,
        word_counts: dict[str, int],
    ) -> None:
        with self.job_manager.word_file_lock:
            for word, frequency in word_counts.items():
                append_word_record(word, relevant_url, origin_url, depth, frequency)

    def _generate_crawler_id(self) -> str:
        return f"{int(time.time())}_{threading.get_ident()}_{int(time.time_ns() % 1_000_000)}"


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _validate_int(name: str, value: int | str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer.") from error

    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return parsed


def _validate_float(name: str, value: float | str, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric.") from error

    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return parsed
