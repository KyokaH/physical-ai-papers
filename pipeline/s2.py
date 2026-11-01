"""Semantic Scholar から TLDR・引用数・採択先を取得する。

API: https://api.semanticscholar.org/graph/v1/paper/batch
- APIキーなしでも使えるが、共有枠なので混雑時は429になりやすい
- APIキーありなら毎秒1リクエスト（環境変数 S2_API_KEY）
"""
from __future__ import annotations

import os
import time

from .common import log, make_session, request_with_retry

BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = "tldr,citationCount,influentialCitationCount,venue,publicationVenue,externalIds"


def parse_batch(ids: list[str], data: list) -> dict[str, dict]:
    """batch API の応答（入力と同じ順のリスト。見つからない論文は null）を変換する。"""
    out = {}
    for arxiv_id, item in zip(ids, data):
        if not item:
            continue
        tldr = (item.get("tldr") or {}).get("text") or ""
        venue = item.get("venue") or ((item.get("publicationVenue") or {}).get("name")) or ""
        out[arxiv_id] = {
            "s2_id": item.get("paperId", ""),
            "tldr_en": tldr.strip(),
            "citations": int(item.get("citationCount") or 0),
            "influential_citations": int(item.get("influentialCitationCount") or 0),
            "venue": venue.strip(),
        }
    return out


def fetch(cfg: dict, arxiv_ids: list[str]) -> dict[str, dict]:
    c = cfg["semantic_scholar"]
    session = make_session()
    key = os.environ.get("S2_API_KEY", "").strip()
    if key:
        session.headers["x-api-key"] = key
    result: dict[str, dict] = {}
    for i in range(0, len(arxiv_ids), c["batch_size"]):
        chunk = arxiv_ids[i:i + c["batch_size"]]
        try:
            resp = request_with_retry(
                session, "POST", BATCH_URL, params={"fields": FIELDS},
                json={"ids": [f"ARXIV:{x}" for x in chunk]},
            )
            result.update(parse_batch(chunk, resp.json()))
            log(f"Semantic Scholar: {i + len(chunk)}/{len(arxiv_ids)}件を問い合わせ")
        except Exception as e:  # 取得できなくても他の処理は続ける
            log(f"Semantic Scholar の取得に失敗（スキップ）: {e}")
        time.sleep(c["request_interval"])
    return result
