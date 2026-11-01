"""根拠バッジ（採択・投稿中・コード・実機）を判定する。

「投稿中（submitted to / under review）」は査読済みと区別する。
"""
from __future__ import annotations

import re

ACCEPT_RE = re.compile(r"accepted|to appear|published|camera[- ]ready|oral|spotlight|"
                       r"in proceedings|proceedings of|award", re.I)
SUBMIT_RE = re.compile(r"submitted to|under review|in submission|under submission", re.I)
GITHUB_RE = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+", re.I)
PROJECT_RE = re.compile(r"https?://[\w.-]+\.github\.io[\w/.-]*", re.I)
ARXIV_VENUE_RE = re.compile(r"^(arxiv(\.org)?|corr|arxiv preprint.*)$", re.I)


def detect_venue(text: str, venues: list[dict]) -> str:
    for v in venues:
        if re.search(v["pattern"], text, re.I):
            return v["name"]
    return ""


def _year(text: str) -> str:
    m = re.search(r"\b(20\d{2})\b", text)
    return m.group(1) if m else ""


def compute(paper: dict, venues: list[dict]) -> dict:
    comment = paper.get("comment", "")
    jref = paper.get("journal_ref", "")
    s2_venue = paper.get("venue", "")
    if ARXIV_VENUE_RE.match(s2_venue.strip()):
        s2_venue = ""

    status, venue, evidence = "", "", ""
    if jref:
        venue = detect_venue(jref, venues) or jref[:40]
        status, evidence = "accepted", "journal_ref"
    elif comment and ACCEPT_RE.search(comment) and detect_venue(comment, venues):
        venue = detect_venue(comment, venues)
        status, evidence = "accepted", "comment"
    elif s2_venue:
        venue = detect_venue(s2_venue, venues) or s2_venue[:40]
        status, evidence = "accepted", "semantic_scholar"
    elif comment and SUBMIT_RE.search(comment) and detect_venue(comment, venues):
        venue = detect_venue(comment, venues)
        status, evidence = "submitted", "comment"
    if venue and status:
        y = _year(jref or comment or "")
        if y and y not in venue:
            venue = f"{venue} {y}"

    text = " ".join([paper.get("abstract", ""), comment])
    code_url = paper.get("github_repo") or ""
    if not code_url:
        m = GITHUB_RE.search(text)
        code_url = m.group(0).rstrip(".,);") if m else ""
    project_url = paper.get("project_page") or ""
    if not project_url:
        m = PROJECT_RE.search(text)
        project_url = m.group(0).rstrip(".,);") if m else ""

    real = (paper.get("llm") or {}).get("real_robot", "unknown")
    return {
        "venue": venue,
        "venue_status": status,      # accepted / submitted / ""
        "venue_evidence": evidence,  # 判定の根拠
        "code_url": code_url,
        "project_url": project_url,
        "real_robot": real,
    }
