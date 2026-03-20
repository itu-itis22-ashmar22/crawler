from __future__ import annotations

from services.job_manager import JobManager
from utils.file_store import read_lines, word_file_path
from utils.ranking import collapse_query_matches, sort_search_results
from utils.tokenizer import tokenize_text


class SearchService:
    def __init__(self, job_manager: JobManager) -> None:
        self.job_manager = job_manager

    def search(self, query: str) -> list[dict]:
        tokens = tokenize_text(query or "")
        if not tokens:
            return []

        normalized_tokens = list(dict.fromkeys(tokens))
        raw_matches: list[dict] = []

        for token in normalized_tokens:
            bucket_path = word_file_path(token)
            with self.job_manager.word_file_lock:
                lines = read_lines(bucket_path)

            for line in lines:
                parts = line.split("\t")
                if len(parts) != 5:
                    continue

                word, relevant_url, origin_url, depth_text, frequency_text = parts
                if word != token:
                    continue

                try:
                    depth = int(depth_text)
                    frequency = int(frequency_text)
                except ValueError:
                    continue

                raw_matches.append(
                    {
                        "relevant_url": relevant_url,
                        "origin_url": origin_url,
                        "depth": depth,
                        "frequency": frequency,
                    }
                )

        collapsed = collapse_query_matches(raw_matches)
        return sort_search_results(collapsed)
