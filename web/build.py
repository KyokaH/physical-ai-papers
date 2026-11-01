"""data/papers の JSON から静的サイト（_site/）を生成する。

実行方法:
  python web/build.py                     # 今日を基準に生成
  python web/build.py --today 2026-10-31  # 基準日を指定（サンプル確認用）
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from pipeline.common import load_config  # noqa: E402
from pipeline.store import DATA_DIR, load_all  # noqa: E402

SOURCE_LABEL = {"s2": "S2", "hf": "HF", "ai": "AI生成", "deepl": "DeepL"}
SOURCE_TITLE = {
    "s2": "Semantic ScholarのTLDRを日本語訳",
    "hf": "Hugging Face PapersのAI要約を日本語訳",
    "ai": "要旨からAIが生成した要約",
    "deepl": "英語TLDRをDeepLで機械翻訳（予備）",
}


def kfmt(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def to_view(p: dict, tag_names: dict) -> dict:
    llm = p.get("llm") or {}
    fb = p.get("fallback_ja") or {}
    b = p.get("badges") or {}
    if llm:
        src = llm.get("tldr_source", "ai")
    elif fb:
        src = "deepl"
    else:
        src = ""
    tags = llm.get("tags") or []
    pub = p.get("published", "")[:10]
    return {
        "id": p["id"],
        "date": pub,
        "title": p.get("title", ""),
        "title_ja": llm.get("title_ja") or fb.get("title_ja") or "",
        "tldr_ja": llm.get("tldr_ja") or fb.get("tldr_ja") or "",
        "tldr_en": p.get("tldr_en") or p.get("hf_summary_en") or "",
        "source": src,
        "source_label": SOURCE_LABEL.get(src, ""),
        "source_title": SOURCE_TITLE.get(src, ""),
        "sections": [(k, llm.get(f)) for k, f in
                     (("課題", "problem"), ("手法", "method"), ("結果", "result"), ("限界", "limitation"))
                     if llm.get(f)],
        "tags": [(t, tag_names.get(t, t)) for t in tags],
        "keywords_ja": llm.get("keywords_ja") or [],
        "keywords_en": llm.get("keywords_en") or [],
        "authors": p.get("authors") or [],
        "abstract": p.get("abstract", ""),
        "comment": p.get("comment", ""),
        "journal_ref": p.get("journal_ref", ""),
        "categories": p.get("categories") or [],
        "abs_url": p.get("abs_url", ""),
        "pdf_url": p.get("pdf_url", ""),
        "venue": b.get("venue", ""),
        "venue_status": b.get("venue_status", ""),
        "venue_evidence": b.get("venue_evidence", ""),
        "code_url": b.get("code_url", ""),
        "project_url": b.get("project_url", ""),
        "real_robot": b.get("real_robot", "unknown"),
        "hf_upvotes": int(p.get("hf_upvotes") or 0),
        "github_stars": int(p.get("github_stars") or 0),
        "citations": int(p.get("citations") or 0),
        "influential": int(p.get("influential_citations") or 0),
        "s2_id": p.get("s2_id", ""),
        "model": llm.get("model", ""),
    }


def age_days(v: dict, today: date) -> int:
    try:
        return (today - date.fromisoformat(v["date"])).days
    except ValueError:
        return 10 ** 6


def score(v: dict, w: dict, use_hf: bool = True) -> tuple[float, list[str]]:
    s, reasons = 0.0, []
    if use_hf and v["hf_upvotes"]:
        s += w["hf_upvotes"] * v["hf_upvotes"]
        reasons.append(f"HFで{v['hf_upvotes']}票")
    if v["github_stars"]:
        s += w["code"] * math.log10(1 + v["github_stars"]) * 3
        reasons.append(f"GitHubスター{kfmt(v['github_stars'])}")
    if v["citations"]:
        s += w["citations"] * v["citations"]
        reasons.append(f"引用{v['citations']}件")
    if v["influential"]:
        s += w["influential_citations"] * v["influential"]
        reasons.append(f"影響力のある引用{v['influential']}件")
    if v["venue_status"] == "accepted":
        s += w["accepted"]
        reasons.append(f"{v['venue']}採択")
    if v["code_url"]:
        s += w["code"]
        if not v["github_stars"]:
            reasons.append("コード公開")
    return s, reasons


def ranking(views: list[dict], today: date, lo: int, hi: int, w: dict, top: int,
            use_hf: bool = True) -> list[dict]:
    rows = []
    for v in views:
        a = age_days(v, today)
        if not (lo <= a < hi):
            continue
        s, reasons = score(v, w, use_hf)
        if s > 0:
            rows.append({**v, "score": round(s, 1), "reasons": reasons})
    rows.sort(key=lambda r: (r["score"], r["date"]), reverse=True)
    return rows[:top]


def build(out: Path, today: date, data_dir: Path) -> None:
    cfg = load_config()
    tag_names = {t["slug"]: t["name"] for t in cfg["tags"]}
    papers = load_all(data_dir)
    views = sorted((to_view(p, tag_names) for p in papers.values()),
                   key=lambda v: (v["date"], v["id"]), reverse=True)
    sb, tr = cfg["site_build"], cfg["trending"]
    w = tr["weights"]

    env = Environment(loader=FileSystemLoader(HERE / "templates"),
                      autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["kfmt"] = kfmt
    built_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    common = {"site": cfg["site"], "today": today.isoformat(), "built_at": built_at,
              "total": len(views), "translated": sum(1 for v in views if v["tldr_ja"])}

    if out.exists():
        shutil.rmtree(out)
    (out / "static").mkdir(parents=True)
    for f in (HERE / "static").iterdir():
        shutil.copy(f, out / "static" / f.name)

    def render(tpl: str, path: str, **ctx):
        depth = path.count("/")
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        html = env.get_template(tpl).render(root="../" * depth or "./", page=path, **common, **ctx)
        target.write_text(html, encoding="utf-8")

    recent = [v for v in views if age_days(v, today) < sb["new_days"]]
    by_date: dict[str, list] = {}
    for v in recent:
        by_date.setdefault(v["date"], []).append(v)

    week = ranking(views, today, 0, tr["week_days"], w, tr["top_n"])
    month = ranking(views, today, 0, tr["month_days"], w, tr["top_n"])
    classic = ranking(views, today, tr["classic_min_days"], tr["classic_max_days"], w, tr["top_n"],
                      use_hf=False)

    tag_counts = []
    for t in cfg["tags"]:
        items = [v for v in views if any(s == t["slug"] for s, _ in v["tags"])]
        tag_counts.append({"slug": t["slug"], "name": t["name"], "total": len(items),
                           "recent": sum(1 for v in items if age_days(v, today) < 30), "items": items})

    latest_days = list(by_date.items())[:3]
    render("index.html", "index.html", week=week[:10], latest_days=latest_days, tags=tag_counts)
    render("new.html", "new/index.html", by_date=list(by_date.items()), days=sb["new_days"])
    render("trending.html", "trending/index.html", week=week, month=month, classic=classic, tr=tr)
    render("tags.html", "tags/index.html", tags=tag_counts)
    for t in tag_counts:
        render("tag.html", f"tags/{t['slug']}/index.html", tag=t, items=t["items"][:sb["tag_page_limit"]])
    for v in views:
        render("paper.html", f"paper/{v['id']}/index.html", p=v)
    render("search.html", "search/index.html", tags=tag_counts)
    render("about.html", "about/index.html", cfg=cfg)

    index = []
    for v in views:
        if age_days(v, today) >= sb["search_days"]:
            continue
        index.append({
            "i": v["id"], "d": v["date"], "t": v["title"], "j": v["title_ja"], "s": v["tldr_ja"],
            "e": v["tldr_en"], "k": v["keywords_ja"] + v["keywords_en"], "g": [s for s, _ in v["tags"]],
            "a": 1 if v["venue_status"] == "accepted" else 0, "c": 1 if v["code_url"] else 0,
            "r": 1 if v["real_robot"] == "yes" else 0, "src": v["source_label"],
            "u": v["hf_upvotes"], "n": v["citations"], "v": v["venue"],
        })
    (out / "search.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")),
                                     encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[site] {len(views)}件の論文から {out} を生成しました（基準日 {today}）", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "_site")
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    a = ap.parse_args(argv)
    build(a.out, a.today or datetime.now(timezone.utc).date(), a.data_dir)


if __name__ == "__main__":
    main()
