"""予備：Geminiが使えない日に、英語のTLDRとタイトルだけを DeepL API Free で翻訳する。

環境変数 DEEPL_API_KEY があるときだけ動く。無料版は月50万文字まで。
https://developers.deepl.com/docs/resources/usage-limits
"""
from __future__ import annotations

import os

from .common import log, make_session, request_with_retry


def _endpoint(key: str) -> str:
    # 無料版のキーは末尾が ":fx"
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    return f"https://{host}/v2/translate"


def run(papers: list[dict], max_papers: int = 150) -> int:
    key = os.environ.get("DEEPL_API_KEY", "").strip()
    if not key:
        return 0
    targets = [p for p in papers if not p.get("llm") and not p.get("fallback_ja")
               and (p.get("tldr_en") or p.get("hf_summary_en"))]
    targets.sort(key=lambda p: p.get("published", ""), reverse=True)
    targets = targets[:max_papers]
    if not targets:
        return 0
    session = make_session()
    session.headers["Authorization"] = f"DeepL-Auth-Key {key}"
    done = 0
    for i in range(0, len(targets), 25):
        chunk = targets[i:i + 25]
        texts = []
        for p in chunk:
            texts += [p["title"], p.get("tldr_en") or p.get("hf_summary_en")]
        try:
            resp = request_with_retry(session, "POST", _endpoint(key),
                                      json={"text": texts, "target_lang": "JA"}, retries=3)
            tr = [t["text"] for t in resp.json()["translations"]]
        except Exception as e:
            log(f"DeepL: 失敗したため中止します: {e}")
            break
        for j, p in enumerate(chunk):
            p["fallback_ja"] = {
                "title_ja": tr[2 * j], "tldr_ja": tr[2 * j + 1],
                "tldr_source": "s2" if p.get("tldr_en") else "hf", "engine": "deepl",
            }
            done += 1
    log(f"DeepL: {done}件を翻訳（予備）")
    return done
