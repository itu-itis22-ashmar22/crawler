from __future__ import annotations

import threading
from datetime import datetime

from utils.file_store import (
    crawler_data_path,
    ensure_storage_layout,
    load_crawler_records,
    load_visited_urls,
    append_visited_url,
    write_json,
)
from utils.url_utils import normalize_url


STALE_JOB_STATUSES = {"queued", "running"}


class JobManager:
    def __init__(self) -> None:
        self.visited_lock = threading.Lock()
        self.job_state_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        self.word_file_lock = threading.Lock()
        self.jobs_by_id: dict[str, dict] = {}
        self.threads_by_id: dict[str, threading.Thread] = {}

        ensure_storage_layout()
        self.visited_urls = load_visited_urls()
        self._load_existing_jobs()

    def _load_existing_jobs(self) -> None:
        for record in load_crawler_records():
            crawler_id = str(record.get("crawler_id", ""))
            if not crawler_id:
                continue

            if record.get("status") in STALE_JOB_STATUSES:
                record["status"] = "interrupted"
                record["updated_at"] = _timestamp()
                write_json(crawler_data_path(crawler_id), record)

            self.jobs_by_id[crawler_id] = dict(record)

    def register_job(self, job_data: dict, thread: threading.Thread | None = None) -> None:
        crawler_id = str(job_data.get("crawler_id", ""))
        if not crawler_id:
            raise ValueError("crawler_id is required")

        with self.job_state_lock:
            self.jobs_by_id[crawler_id] = dict(job_data)
            write_json(crawler_data_path(crawler_id), self.jobs_by_id[crawler_id])
            if thread is not None:
                self.threads_by_id[crawler_id] = thread

    def update_job(self, crawler_id: str, updates: dict) -> dict:
        with self.job_state_lock:
            current = dict(self.jobs_by_id.get(crawler_id, {}))
            current.update(updates)
            self.jobs_by_id[crawler_id] = current
            write_json(crawler_data_path(crawler_id), current)
            return dict(current)

    def get_job(self, crawler_id: str) -> dict | None:
        with self.job_state_lock:
            job = self.jobs_by_id.get(crawler_id)
            return dict(job) if job else None

    def list_jobs(self) -> list[dict]:
        with self.job_state_lock:
            jobs = [dict(job) for job in self.jobs_by_id.values()]
        return sorted(jobs, key=lambda job: str(job.get("created_at", "")), reverse=True)

    def mark_visited(self, url: str) -> bool:
        normalized_url = normalize_url(url)
        if not normalized_url:
            return False

        with self.visited_lock:
            if normalized_url in self.visited_urls:
                return False
            self.visited_urls.add(normalized_url)
            append_visited_url(normalized_url)
            return True


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")
