"""Gemini API（OpenAI互換エンドポイント）で、日本語TLDR・タグ・検索用キーワードを作る。

- 20件程度をまとめて1回の依頼にし、無料枠の回数上限に収まりやすくする
- 既存の英語TLDR（S2 / HF）があればそれを翻訳し、なければ要旨から一文要約を作る
- 1日の上限に達したら残りを pending のまま残し、次回の実行で続きを処理する
参考：https://ai.google.dev/gemini-api/docs/openai
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from .common import log, make_session

SYSTEM_PROMPT = """あなたはロボティクスとPhysical AIの研究に詳しい、正確さを最優先する技術翻訳者です。
与えられた論文の情報だけを根拠に、日本語の要約データを作ります。推測で情報を足してはいけません。

各論文について次を作ってください。
- title_ja: タイトルの自然な日本語訳。手法名・モデル名（例: RT-2, π0）は英語のまま残す
- tldr_ja: 一文の日本語要約（全角100字以内）
  - source_summary がある場合: その英文を忠実に日本語へ翻訳する。情報を足さない
  - source_summary が空の場合: abstract から「何を・どうやって・どれくらい良くなったか」を一文でまとめる
- problem / method / result / limitation: 課題・手法・結果・限界をそれぞれ全角80字以内で。
  abstract に書かれていない項目は「要旨に記載なし」とする（特に limitation）
- tags: 次の候補から1〜3個（slugで回答）: {tags}
- keywords_ja: 日本語で検索されそうな語を5〜10個（例: 把持, 二足歩行, 言語指示, 実機実験）
- keywords_en: 英語の重要語を3〜8個（例: dexterous grasping, diffusion policy）
- real_robot: 実機ロボットでの実験が abstract に明記されていれば "yes"、シミュレーションのみと明記されていれば "no"、判断できなければ "unknown"

出力は次の形のJSONオブジェクトだけにしてください（説明文やコードブロックは不要）:
{{"papers": [{{"id": "...", "title_ja": "...", "tldr_ja": "...", "problem": "...", "method": "...", "result": "...", "limitation": "...", "tags": ["..."], "keywords_ja": ["..."], "keywords_en": ["..."], "real_robot": "yes|no|unknown"}}]}}
入力された全論文について、同じ id で必ず1件ずつ返してください。"""

FIELDS = ("title_ja", "tldr_ja", "problem", "method", "result", "limitation")


class QuotaExhausted(Exception):
    """1日の無料枠を使い切ったと判断したとき。"""


def _base_url(cfg: dict) -> str:
    url = os.environ.get("LLM_BASE_URL") or cfg["llm"]["base_url"]
    return url if url.endswith("/") else url + "/"


def _api_key() -> str:
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY") or "").strip()


def choose_model(cfg: dict, session: requests.Session) -> str:
    """設定・環境変数で指定がなければ、使えるモデル一覧からFlash-Lite系を選ぶ。"""
    explicit = (os.environ.get("GEMINI_MODEL") or cfg["llm"].get("model") or "").strip()
    if explicit:
        return explicit
    resp = session.get(_base_url(cfg) + "models",
                       headers={"Authorization": f"Bearer {_api_key()}"}, timeout=30)
    resp.raise_for_status()
    ids = [m.get("id", "").replace("models/", "") for m in resp.json().get("data", [])]
    model = pick_model(ids)
    if not model:
        raise RuntimeError(f"利用できるモデルが見つかりません: {ids[:20]}")
    log(f"LLM: モデルを自動選択しました → {model}")
    return model


def pick_model(ids: list[str]) -> str:
    bad = ("preview", "exp", "image", "tts", "audio", "live", "embedding", "thinking", "vision")

    def version(i: str) -> tuple:
        return tuple(int(x) for x in re.findall(r"\d+", i.split("-")[1] if "-" in i else "0")) or (0,)

    for want in ("flash-lite", "flash"):
        cands = [i for i in ids if i.startswith("gemini-") and want in i
                 and not any(b in i for b in bad)]
        if want == "flash":
            cands = [i for i in cands if "flash-lite" not in i]
        if cands:
            return sorted(cands, key=lambda i: (version(i), -len(i)), reverse=True)[0]
    return ""


def build_user_message(cfg: dict, batch: list[dict]) -> str:
    limit = cfg["llm"]["abstract_max_chars"]
    items = []
    for p in batch:
        items.append({
            "id": p["id"],
            "title": p["title"],
            "abstract": p["abstract"][:limit],
            "source_summary": p.get("tldr_en") or p.get("hf_summary_en") or "",
            "comment": p.get("comment", ""),
        })
    return json.dumps({"papers": items}, ensure_ascii=False)


def parse_response(text: str, allowed_tags: set[str]) -> dict[str, dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    if not text.startswith("{"):
        m = re.search(r"\{.*\}", text, re.S)
        text = m.group(0) if m else "{}"
    data = json.loads(text)
    out = {}
    for item in data.get("papers", []):
        pid = str(item.get("id", "")).strip()
        if not pid:
            continue
        rec = {k: str(item.get(k, "") or "").strip() for k in FIELDS}
        tags = [t for t in (item.get("tags") or []) if t in allowed_tags][:3]
        rec["tags"] = tags or ["other"]
        rec["keywords_ja"] = [str(x).strip() for x in (item.get("keywords_ja") or []) if str(x).strip()][:10]
        rec["keywords_en"] = [str(x).strip() for x in (item.get("keywords_en") or []) if str(x).strip()][:8]
        rr = str(item.get("real_robot", "unknown")).lower()
        rec["real_robot"] = rr if rr in ("yes", "no", "unknown") else "unknown"
        if rec["tldr_ja"]:
            out[pid] = rec
    return out


class GeminiClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.session = make_session()
        self.key = _api_key()
        if not self.key:
            raise RuntimeError("GEMINI_API_KEY が設定されていません")
        self.model = choose_model(cfg, self.session)
        self.use_json_mode = True
        self.allowed_tags = {t["slug"] for t in cfg["tags"]}
        tag_list = ", ".join(f'{t["slug"]}（{t["name"]}）' for t in cfg["tags"])
        self.system = SYSTEM_PROMPT.format(tags=tag_list)

    def _post(self, messages: list[dict]) -> str:
        body = {"model": self.model, "messages": messages, "temperature": 0.2}
        if self.use_json_mode:
            body["response_format"] = {"type": "json_object"}
        url = _base_url(self.cfg) + "chat/completions"
        headers = {"Authorization": f"Bearer {self.key}"}
        for attempt in range(5):
            resp = self.session.post(url, json=body, headers=headers, timeout=180)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"] or ""
            msg = resp.text[:300]
            if resp.status_code == 400 and self.use_json_mode and "response_format" in msg:
                self.use_json_mode = False  # JSONモード非対応のモデルなら外して再試行
                body.pop("response_format", None)
                continue
            if resp.status_code == 429:
                if re.search(r"per ?day|PerDay|daily", msg, re.I):
                    raise QuotaExhausted(msg)
                wait = 30 * (attempt + 1)
                log(f"LLM: 回数上限（429）。{wait}秒待って再試行")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(f"LLM HTTP {resp.status_code}: {msg}")
        raise QuotaExhausted("再試行の上限に達しました")

    def enrich(self, batch: list[dict]) -> dict[str, dict]:
        messages = [{"role": "system", "content": self.system},
                    {"role": "user", "content": build_user_message(self.cfg, batch)}]
        text = self._post(messages)
        try:
            return parse_response(text, self.allowed_tags)
        except (json.JSONDecodeError, ValueError) as e:
            log(f"LLM: 応答のJSONを読めませんでした（{e}）。この塊は次回に回します")
            return {}


def run(cfg: dict, papers: list[dict], client=None) -> int:
    """llm 未処理の論文を新しい順に処理し、論文の辞書に結果を書き込む。処理件数を返す。"""
    pending = [p for p in papers if not p.get("llm")]
    pending.sort(key=lambda p: p.get("published", ""), reverse=True)
    pending = pending[: cfg["llm"]["max_papers_per_run"]]
    if not pending:
        return 0
    try:
        client = client or GeminiClient(cfg)
    except Exception as e:
        log(f"LLM を使えないため日本語化をスキップします: {e}")
        return 0
    size = cfg["llm"]["batch_size"]
    done = 0
    for i in range(0, len(pending), size):
        batch = pending[i:i + size]
        try:
            results = client.enrich(batch)
        except QuotaExhausted as e:
            log(f"LLM: 本日の無料枠を使い切ったようです。残りは次回処理します（{str(e)[:120]}）")
            break
        except Exception as e:
            log(f"LLM: 失敗（この塊はスキップ）: {e}")
            results = {}
        for p in batch:
            r = results.get(p["id"])
            if r:
                r["model"] = getattr(client, "model", "")
                r["tldr_source"] = "s2" if p.get("tldr_en") else ("hf" if p.get("hf_summary_en") else "ai")
                p["llm"] = r
                p.pop("fallback_ja", None)
                done += 1
        log(f"LLM: {min(i + size, len(pending))}/{len(pending)}件を処理（成功 {done}件）")
        if i + size < len(pending):
            time.sleep(cfg["llm"]["request_interval"])
    return done
