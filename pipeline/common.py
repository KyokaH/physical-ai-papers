"""共通処理：設定の読み込み、HTTP、ログ。"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "physical-ai-papers/1.0 (personal paper digest; https://github.com/)"


def log(*args) -> None:
    print("[pipeline]", *args, file=sys.stderr, flush=True)


def load_config(path: Path | None = None) -> dict:
    path = path or ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_session() -> requests.Session:
    s = requests.Session()
    contact = os.environ.get("CONTACT_EMAIL", "").strip()
    ua = USER_AGENT if not contact else f"{USER_AGENT} mailto:{contact}"
    s.headers.update({"User-Agent": ua})
    return s


def request_with_retry(session: requests.Session, method: str, url: str, *,
                       retries: int = 5, backoff: float = 5.0, ok_status=(200,),
                       **kwargs) -> requests.Response:
    """429や5xxのときは待ってから再試行する。最後まで失敗したら例外を投げる。"""
    kwargs.setdefault("timeout", 60)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = session.request(method, url, **kwargs)
        except requests.RequestException as e:  # 通信エラー
            last_exc = e
            wait = backoff * (2 ** attempt)
            log(f"通信エラー（{e.__class__.__name__}）。{wait:.0f}秒後に再試行: {url}")
            time.sleep(wait)
            continue
        if resp.status_code in ok_status:
            return resp
        if resp.status_code == 429 or resp.status_code >= 500:
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff * (2 ** attempt)
            log(f"HTTP {resp.status_code}。{wait:.0f}秒後に再試行: {url}")
            time.sleep(wait)
            last_exc = requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            continue
        resp.raise_for_status()
        return resp
    raise last_exc or RuntimeError(f"request failed: {url}")
