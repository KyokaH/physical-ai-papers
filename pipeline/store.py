"""論文データを月ごとのJSONファイル（data/papers/YYYY-MM.json）に保存する。"""
from __future__ import annotations

import json
from pathlib import Path

from .common import ROOT

DATA_DIR = ROOT / "data" / "papers"


def load_all(data_dir: Path = DATA_DIR) -> dict[str, dict]:
    papers: dict[str, dict] = {}
    for f in sorted(data_dir.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            papers.update(json.load(fh))
    return papers


def save_all(papers: dict[str, dict], data_dir: Path = DATA_DIR) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, dict] = {}
    for pid, p in papers.items():
        month = (p.get("published") or "0000-00")[:7]
        by_month.setdefault(month, {})[pid] = p
    for month, items in by_month.items():
        path = data_dir / f"{month}.json"
        ordered = dict(sorted(items.items(), key=lambda kv: kv[1].get("published", ""), reverse=True))
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(ordered, fh, ensure_ascii=False, indent=1)
        tmp.replace(path)
