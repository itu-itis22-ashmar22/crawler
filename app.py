from __future__ import annotations

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from services.crawler_service import CrawlerService
from services.job_manager import JobManager
from services.search_service import SearchService
from utils.file_store import crawler_log_path, crawler_queue_path, read_lines, tail_lines


app = Flask(__name__, template_folder="demo/templates", static_folder="demo/static")

job_manager = JobManager()
crawler_service = CrawlerService(job_manager)
search_service = SearchService(job_manager)


@app.get("/")
def index():
    return redirect(url_for("crawler_home"))


@app.get("/crawler")
def crawler_home():
    return render_template(
        "crawler.html",
        jobs=crawler_service.list_crawlers(),
        error_message="",
        form_data=_default_crawler_form(),
    )


@app.post("/crawler")
def create_crawler():
    form_data = {
        "origin_url": request.form.get("origin_url", "").strip(),
        "max_depth": request.form.get("max_depth", "1").strip(),
        "hit_rate_seconds": request.form.get("hit_rate_seconds", "1").strip(),
        "max_urls_to_visit": request.form.get("max_urls_to_visit", "10").strip(),
        "queue_capacity": request.form.get("queue_capacity", "50").strip(),
    }
    try:
        crawler_id = crawler_service.create_crawler(
            origin_url=form_data["origin_url"],
            max_depth=form_data["max_depth"],
            hit_rate_seconds=form_data["hit_rate_seconds"],
            max_urls_to_visit=form_data["max_urls_to_visit"],
            queue_capacity=form_data["queue_capacity"],
        )
    except ValueError as error:
        return render_template(
            "crawler.html",
            jobs=crawler_service.list_crawlers(),
            error_message=str(error),
            form_data=form_data,
        )

    return redirect(url_for("crawler_status_page", crawler_id=crawler_id))


@app.get("/crawler/<crawler_id>")
def crawler_status_page(crawler_id: str):
    status_payload = _crawler_status_payload(crawler_id)
    if status_payload is None:
        abort(404)
    return render_template("crawler_status.html", crawler=status_payload)


@app.get("/api/crawler/<crawler_id>/status")
def crawler_status_api(crawler_id: str):
    status_payload = _crawler_status_payload(crawler_id)
    if status_payload is None:
        return jsonify({"error": "Crawler not found"}), 404
    return jsonify(status_payload)


@app.get("/search")
def search_page():
    query = request.args.get("query", "").strip()
    results = search_service.search(query) if query else []
    return render_template(
        "search.html",
        query=query,
        results=results,
        total_count=len(results),
    )


def _crawler_status_payload(crawler_id: str) -> dict | None:
    crawler = crawler_service.get_crawler_status(crawler_id)
    if crawler is None:
        return None

    queue_preview = read_lines(crawler_queue_path(crawler_id))[:25]
    log_tail = tail_lines(crawler_log_path(crawler_id), 100)
    payload = dict(crawler)
    payload["queue_preview"] = queue_preview
    payload["log_tail"] = log_tail
    return payload


def _default_crawler_form() -> dict[str, str]:
    return {
        "origin_url": "",
        "max_depth": "1",
        "hit_rate_seconds": "1",
        "max_urls_to_visit": "10",
        "queue_capacity": "50",
    }


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
