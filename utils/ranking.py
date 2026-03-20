from __future__ import annotations


def collapse_query_matches(raw_matches: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, int], dict] = {}
    for match in raw_matches:
        key = (
            str(match.get("relevant_url", "")),
            str(match.get("origin_url", "")),
            int(match.get("depth", 0)),
        )
        if key not in grouped:
            grouped[key] = {
                "relevant_url": key[0],
                "origin_url": key[1],
                "depth": key[2],
                "total_frequency": 0,
            }
        grouped[key]["total_frequency"] += int(match.get("frequency", 0))
    return list(grouped.values())


def sort_search_results(results: list[dict]) -> list[dict]:
    return sorted(
        results,
        key=lambda item: (
            -int(item.get("total_frequency", 0)),
            int(item.get("depth", 0)),
            str(item.get("relevant_url", "")),
        ),
    )
