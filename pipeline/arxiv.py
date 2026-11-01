"""arXiv API から新着論文を取得する。

規約：https://info.arxiv.org/help/api/tou.html
- メタデータ（タイトル・要旨など）は CC0
- 3秒に1リクエスト・同時接続1本まで
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from .common import log, make_session, request_with_retry

API_URL = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
ID_RE = re.compile(r"arxiv\.org/abs/([^v\s]+?)(v\d+)?$")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_feed(xml_text: str) -> tuple[list[dict], int]:
    """Atomフィードを論文の辞書のリストに変換する。（論文リスト, 総件数）を返す。"""
    root = ET.fromstring(xml_text)
    total_el = root.find("opensearch:totalResults", NS)
    total = int(total_el.text) if total_el is not None and total_el.text else 0
    papers = []
    for entry in root.findall("atom:entry", NS):
        raw_id = _clean(entry.findtext("atom:id", default="", namespaces=NS))
        m = ID_RE.search(raw_id)
        if not m:
            continue  # エラー応答など
        arxiv_id = m.group(1)
        version = (m.group(2) or "v1")[1:]
        pdf_url = ""
        for link in entry.findall("atom:link", NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
        primary = entry.find("arxiv:primary_category", NS)
        papers.append({
            "id": arxiv_id,
            "version": int(version) if version.isdigit() else 1,
            "title": _clean(entry.findtext("atom:title", default="", namespaces=NS)),
            "abstract": _clean(entry.findtext("atom:summary", default="", namespaces=NS)),
            "authors": [_clean(a.findtext("atom:name", default="", namespaces=NS))
                        for a in entry.findall("atom:author", NS)],
            "published": _clean(entry.findtext("atom:published", default="", namespaces=NS)),
            "updated": _clean(entry.findtext("atom:updated", default="", namespaces=NS)),
            "primary_category": primary.get("term", "") if primary is not None else "",
            "categories": [c.get("term", "") for c in entry.findall("atom:category", NS)],
            "comment": _clean(entry.findtext("arxiv:comment", default="", namespaces=NS)),
            "journal_ref": _clean(entry.findtext("arxiv:journal_ref", default="", namespaces=NS)),
            "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
        })
    return papers, total


def build_queries(cfg: dict, start: datetime, end: datetime) -> list[str]:
    a = cfg["arxiv"]
    date = f"submittedDate:[{start:%Y%m%d%H%M} TO {end:%Y%m%d%H%M}]"
    queries = []
    prim = " OR ".join(f"cat:{c}" for c in a["primary_categories"])
    queries.append(f"({prim}) AND {date}")
    if a.get("secondary_categories") and a.get("secondary_keywords"):
        sec = " OR ".join(f"cat:{c}" for c in a["secondary_categories"])
        kws = " OR ".join(f'abs:"{k}"' if " " in k or "-" in k else f"abs:{k}"
                          for k in a["secondary_keywords"])
        queries.append(f"({sec}) AND ({kws}) AND {date}")
    return queries


def fetch_recent(cfg: dict, days: int, now: datetime | None = None) -> list[dict]:
    """直近 days 日に投稿された論文を取得する（IDで重複を除く）。"""
    a = cfg["arxiv"]
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    session = make_session()
    found: dict[str, dict] = {}
    for q in build_queries(cfg, start, now):
        offset = 0
        while offset < a["max_results"]:
            params = {
                "search_query": q,
                "start": offset,
                "max_results": a["page_size"],
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            resp = request_with_retry(session, "GET", API_URL, params=params)
            papers, total = parse_feed(resp.text)
            for p in papers:
                found.setdefault(p["id"], p)
            log(f"arXiv: {len(papers)}件取得（{offset + len(papers)}/{total}） query={q[:60]}…")
            offset += a["page_size"]
            time.sleep(a["request_interval"])
            if not papers or offset >= total:
                break
    return list(found.values())
