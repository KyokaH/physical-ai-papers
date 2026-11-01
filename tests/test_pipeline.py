import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIX = ROOT / "tests" / "fixtures"

from pipeline import arxiv, badges, hf, llm, s2  # noqa: E402
from pipeline.common import load_config  # noqa: E402
from pipeline.run import main as run_main  # noqa: E402

CFG = load_config()


def test_parse_arxiv_feed():
    papers, total = arxiv.parse_feed((FIX / "arxiv.xml").read_text(encoding="utf-8"))
    assert total == len(papers) == 12
    p = next(x for x in papers if x["id"] == "2610.21001")
    assert p["version"] == 1
    assert p["comment"].startswith("Accepted to CoRL")
    assert p["primary_category"] == "cs.RO"
    assert "Taro Example" in p["authors"]


def test_queries_include_date_and_keywords():
    from datetime import datetime, timezone
    qs = arxiv.build_queries(CFG, datetime(2026, 10, 1, tzinfo=timezone.utc), datetime(2026, 10, 4, tzinfo=timezone.utc))
    assert qs[0].startswith("(cat:cs.RO)") and "submittedDate:[202610010000 TO 202610040000]" in qs[0]
    assert 'abs:"vision-language-action"' in qs[1]


def test_s2_and_hf_parsing():
    ids = json.loads((FIX / "s2_ids.json").read_text())
    data = s2.parse_batch(ids, json.loads((FIX / "s2.json").read_text()))
    assert data["2610.21001"]["citations"] == 12
    assert data["2610.21002"]["tldr_en"] == ""
    assert "2610.21004" not in data  # null の論文は飛ばす
    h = hf.parse_daily(json.loads((FIX / "hf.json").read_text()))
    assert h["2610.21001"]["hf_upvotes"] == 214 and h["2610.21001"]["github_stars"] == 1200


def test_badges_distinguish_submitted_and_accepted():
    v = CFG["venues"]
    acc = badges.compute({"comment": "Accepted to CoRL 2026", "abstract": ""}, v)
    sub = badges.compute({"comment": "Submitted to ICRA 2027", "abstract": ""}, v)
    pre = badges.compute({"comment": "8 pages", "abstract": "", "venue": "arXiv.org"}, v)
    assert (acc["venue_status"], acc["venue"]) == ("accepted", "CoRL 2026")
    assert (sub["venue_status"], sub["venue"]) == ("submitted", "ICRA 2027")
    assert pre["venue_status"] == ""
    code = badges.compute({"abstract": "Code: https://github.com/a/b.", "comment": ""}, v)
    assert code["code_url"] == "https://github.com/a/b"


def test_llm_response_parsing_and_model_pick():
    text = '```json\n{"papers":[{"id":"x","title_ja":"題","tldr_ja":"要約","tags":["vla","bogus"],"real_robot":"maybe"}]}\n```'
    r = llm.parse_response(text, {"vla", "other"})
    assert r["x"]["tags"] == ["vla"] and r["x"]["real_robot"] == "unknown"
    ids = ["gemini-2.0-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash-lite-preview",
           "gemini-3.8-flash", "text-embedding-004"]
    assert llm.pick_model(ids) == "gemini-3.5-flash-lite"
    assert llm.pick_model(["gemini-3.8-flash", "gemini-2.0-flash"]) == "gemini-3.8-flash"


def test_llm_run_stops_on_quota():
    class Fake:
        model = "fake"
        calls = 0

        def enrich(self, batch):
            Fake.calls += 1
            if Fake.calls > 1:
                raise llm.QuotaExhausted("per day")
            return {p["id"]: {"tldr_ja": "x", "tags": ["other"]} for p in batch}

    cfg = {**CFG, "llm": {**CFG["llm"], "batch_size": 2, "request_interval": 0}}
    papers = [{"id": str(i), "published": f"2026-10-{i + 10}"} for i in range(5)]
    assert llm.run(cfg, papers, client=Fake()) == 2
    assert sum(1 for p in papers if p.get("llm")) == 2  # 残りは次回に回る


def test_end_to_end_offline(tmp_path):
    data = tmp_path / "data"
    run_main(["--offline", str(FIX), "--data-dir", str(data)])
    stored = json.loads((data / "2026-10.json").read_text(encoding="utf-8"))
    assert stored["2610.21001"]["llm"]["tldr_source"] == "s2"
    assert stored["2610.21004"]["llm"]["tldr_source"] == "hf"
    assert stored["2610.21002"]["llm"]["tldr_source"] == "ai"

    sys.path.insert(0, str(ROOT / "web"))
    import build  # noqa: E402
    out = tmp_path / "site"
    build.build(out, date(2026, 10, 31), data)
    assert (out / "paper" / "2610.21001" / "index.html").exists()
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "今週の注目" in index and "採択 CoRL 2026" in index
    search = json.loads((out / "search.json").read_text(encoding="utf-8"))
    assert any(x["i"] == "2610.21010" and "把持" in x["k"] for x in search)
