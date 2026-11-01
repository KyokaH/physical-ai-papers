"""毎日の処理をまとめて実行する。

使い方:
  python -m pipeline.run                # 直近3日分を取得（通常の毎日実行）
  python -m pipeline.run --days 14      # 初回など、さかのぼって取得
  python -m pipeline.run --offline tests/fixtures   # ネットに接続せずサンプルで試す
  python -m pipeline.run --skip-llm     # 日本語化をせず、収集と指標の更新だけ行う
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import arxiv, badges, deepl, hf, llm, s2, store
from .common import load_config, log

MERGE_FROM_ARXIV = ("version", "title", "abstract", "authors", "updated", "primary_category",
                    "categories", "comment", "journal_ref", "abs_url", "pdf_url")


def merge_arxiv(papers: dict, fetched: list[dict]) -> int:
    new = 0
    for f in fetched:
        cur = papers.get(f["id"])
        if cur is None:
            papers[f["id"]] = f
            new += 1
            continue
        title_changed = cur.get("title") != f["title"] or cur.get("abstract") != f["abstract"]
        for k in MERGE_FROM_ARXIV:
            cur[k] = f[k]
        if title_changed:
            cur.pop("llm", None)  # 改訂で内容が変わったら日本語化をやり直す
    return new


def apply_metrics(papers: dict, s2_data: dict, hf_data: dict) -> None:
    for pid, m in s2_data.items():
        if pid in papers:
            papers[pid].update(m)
    for pid, m in hf_data.items():
        if pid in papers:
            papers[pid].update(m)


class OfflineLLM:
    """--offline 用。fixtures/llm.json の応答を返す。"""

    def __init__(self, cfg: dict, path: Path):
        self.model = "offline-fixture"
        self.allowed = {t["slug"] for t in cfg["tags"]}
        self.text = path.read_text(encoding="utf-8")

    def enrich(self, batch):
        res = llm.parse_response(self.text, self.allowed)
        return {p["id"]: res[p["id"]] for p in batch if p["id"] in res}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--offline", type=Path, help="サンプルデータのディレクトリ")
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--data-dir", type=Path, default=store.DATA_DIR)
    args = ap.parse_args(argv)

    cfg = load_config()
    now = datetime.now(timezone.utc)
    papers = store.load_all(args.data_dir)
    log(f"保存済みの論文: {len(papers)}件")

    # 1. arXiv
    if args.offline:
        fetched, _ = arxiv.parse_feed((args.offline / "arxiv.xml").read_text(encoding="utf-8"))
    else:
        fetched = arxiv.fetch_recent(cfg, args.days, now)
    log(f"新規 {merge_arxiv(papers, fetched)}件（取得 {len(fetched)}件）")

    # 2. Semantic Scholar（直近 refresh_days 日の論文の指標を更新）
    cutoff = (now - timedelta(days=cfg["semantic_scholar"]["refresh_days"])).isoformat()
    targets = [pid for pid, p in papers.items() if p.get("published", "") >= cutoff or args.offline]
    if args.offline:
        ids = json.loads((args.offline / "s2_ids.json").read_text(encoding="utf-8"))
        s2_data = s2.parse_batch(ids, json.loads((args.offline / "s2.json").read_text(encoding="utf-8")))
    else:
        s2_data = s2.fetch(cfg, targets)

    # 3. Hugging Face
    if args.offline:
        hf_data = hf.parse_daily(json.loads((args.offline / "hf.json").read_text(encoding="utf-8")))
    else:
        hf_data = hf.fetch(cfg, now)
    apply_metrics(papers, s2_data, hf_data)

    # 4. 日本語化（Gemini）。上限に達したら DeepL で翻訳だけ行う
    plist = list(papers.values())
    if not args.skip_llm:
        client = OfflineLLM(cfg, args.offline / "llm.json") if args.offline else None
        n = llm.run(cfg, plist, client=client)
        log(f"日本語化: {n}件")
        deepl.run(plist)

    # 5. 根拠バッジ
    for p in plist:
        p["badges"] = badges.compute(p, cfg["venues"])
        p["fetched_at"] = p.get("fetched_at") or now.isoformat(timespec="seconds")
    p_pending = sum(1 for p in plist if not p.get("llm"))
    log(f"日本語化が未処理の論文: {p_pending}件（次回以降に処理）")

    store.save_all(papers, args.data_dir)
    log("保存しました")


if __name__ == "__main__":
    main()
