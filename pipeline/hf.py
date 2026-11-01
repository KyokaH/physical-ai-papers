"""Hugging Face Daily Papers から注目度（upvote）・コード・AI要約を取得する。

API: https://huggingface.co/api/daily_papers?date=YYYY-MM-DD
応答の形が変わっても止まらないよう、値は存在する場合だけ読む。
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from .common import log, make_session, request_with_retry

API_URL = "https://huggingface.co/api/daily_papers"


def _first(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


def parse_daily(data: list) -> dict[str, dict]:
    out = {}
    for item in data or []:
        paper = item.get("paper") or item
        arxiv_id = paper.get("id") or item.get("id")
        if not arxiv_id:
            continue
        out[arxiv_id] = {
            "hf_upvotes": int(_first(paper, "upvotes", default=0) or _first(item, "upvotes", default=0) or 0),
            "hf_comments": int(_first(item, "numComments", default=0) or 0),
            "hf_summary_en": (_first(paper, "ai_summary", "aiSummary", default="") or "").strip(),
            "github_repo": _first(paper, "githubRepo", default="") or _first(item, "githubRepo", default="") or "",
            "github_stars": int(_first(paper, "githubStars", default=0) or _first(item, "githubStars", default=0) or 0),
            "project_page": _first(paper, "projectPage", default="") or "",
        }
    return out


def fetch(cfg: dict, now: datetime | None = None) -> dict[str, dict]:
    days = cfg["huggingface"]["lookback_days"]
    now = now or datetime.now(timezone.utc)
    session = make_session()
    result: dict[str, dict] = {}
    for d in range(days + 1):
        date = (now - timedelta(days=d)).strftime("%Y-%m-%d")
        try:
            resp = request_with_retry(session, "GET", API_URL,
                                      params={"date": date, "limit": 100}, retries=3)
            result.update(parse_daily(resp.json()))
        except Exception as e:
            log(f"HF Papers {date} の取得に失敗（スキップ）: {e}")
        time.sleep(1.0)
    log(f"HF Papers: {len(result)}件の注目度を取得")
    return result
