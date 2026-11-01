# PhysicalAI 論文ウォッチ

PhysicalAI と Robotics の新着論文を、**日本語の一文要約（TLDR）**と**根拠バッジ**（採択・コード・実機評価）付きで一覧する、自分用の静的サイトです。

- GitHub Actions が毎日、論文の収集・日本語化・サイトの更新までを自動で行います
- サーバーは不要で、GitHub Pages で公開します
- 費用は無料です（Gemini API の無料枠を使います）

```
arXiv (cs.RO＋関連語) ─┐
Semantic Scholar ──────┼─> 収集・ID統合 ─> 要約を探す（S2 → HF → Gemini生成）
Hugging Face Papers ───┘        ─> 日本語化・タグ・根拠バッジ ─> data/papers/*.json ─> GitHub Pages
```

## ページ構成

| ページ | 内容 |
|---|---|
| トップ | 分類ごとの件数、今週の注目トップ10、直近3日の新着 |
| 新着 | 過去14日分を日付ごとに表示 |
| 注目論文 | 今週（HFの票・スター）、今月（＋引用数）、定番（30日〜1年前、引用と採択） |
| 分類 | 分類ごとの一覧 |
| 論文ページ `/paper/{arXiv ID}/` | 一文要約、根拠の表、課題・手法・結果・限界、原文リンク |
| 検索 | 日本語で入力すると英語の言葉にも広げて探します。採択済み・コードあり・実機評価ありで絞り込めます |

要約の横の印は、要約の出どころを表します。

| 印 | 出どころ |
|---|---|
| `S2` | Semantic Scholar の TLDR の和訳 |
| `HF` | Hugging Face Papers の AI 要約の和訳 |
| `AI生成` | 上の2つがないときに、Gemini が要旨から作ったもの |
| `DeepL` | Gemini を使えなかった日の予備翻訳 |

---

## 導入手順（15分ほど）

### 1. リポジトリを作る
1. GitHub で新しいリポジトリを作ります。名前は例えば `physical-ai-papers` とし、**Public** にします（無料プランの GitHub Pages は公開リポジトリでしか使えないため）。
2. このフォルダの中身をすべてプッシュします。
   ```bash
   cd physical-ai-papers
   git init && git add . && git commit -m "first commit"
   git branch -M main
   git remote add origin https://github.com/<あなたのユーザー名>/physical-ai-papers.git
   git push -u origin main
   ```

### 2. Gemini の API キーを登録する（必須）
1. [Google AI Studio](https://aistudio.google.com/apikey) に Google アカウントでログインし、API キーを作ります。課金の設定は不要です。
2. GitHub のリポジトリで **Settings → Secrets and variables → Actions → New repository secret** を開き、次を登録します。
   - Name: `GEMINI_API_KEY`
   - Secret: 発行したキー

### 3. 任意の設定
同じ画面で登録します。なくても動きます。

| 種類 | 名前 | 用途 |
|---|---|---|
| Secret | `S2_API_KEY` | Semantic Scholar の API キー。あると混雑時にも安定します（[申請ページ](https://www.semanticscholar.org/product/api)） |
| Secret | `DEEPL_API_KEY` | Gemini の無料枠を使い切った日に、DeepL API Free で翻訳だけ行います |
| Variable | `GEMINI_MODEL` | 使うモデルを固定したいときに指定します（例 `gemini-3.5-flash-lite`）。空欄なら、使えるモデルから Flash-Lite 系を自動で選びます |
| Variable | `CONTACT_EMAIL` | arXiv などへのアクセス時に連絡先として名乗るメールアドレス |

### 4. GitHub Pages を有効にする
**Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。

### 5. 初回の実行
1. **Actions** タブで「論文の収集とサイト更新」を開き、**Run workflow** を押します。
2. `days` に `14` を入れて実行すると、過去2週間分を取得します。
3. 終わると `https://<ユーザー名>.github.io/physical-ai-papers/` でサイトが見られます。

以降は毎日 日本時間10:17ごろに自動で更新されます。

---

## 無料枠について

- Gemini への依頼は **20本ずつまとめて** 送ります。1日あたり数十回の依頼で済む計算です。
- 1日の上限に達した場合、残りの論文は「日本語化待ち」のまま保存され、**次回の実行で続きから**処理されます。
- 無料枠の上限は Google 側で変わることがあります。最新の値は AI Studio で確認してください。
- 無料枠では、送った内容が Google の製品改善に使われることがあります。このサイトが送るのは、公開済みの arXiv の要旨だけです。

## 公開範囲について

無料プランの GitHub Pages は誰でも閲覧できます。そのため、すべてのページを検索エンジンに載らない設定（`noindex` と `robots.txt`）にしてあります。URL を知っている人は見られる点に注意してください。

---

## 調整のしかた

`config.yaml` を編集して、変更をコミットします。

- **取得する論文**：`arxiv.secondary_keywords` に語を足すと、cs.CV・cs.LG・cs.AI から拾う範囲が広がります
- **分類タグ**：`tags` を編集します（`slug` は英数字）
- **採択の判定に使う会議**：`venues` に名前と正規表現を足します
- **注目度の重み**：`trending.weights` を変えます
- **検索の日本語→英語の対応表**：`web/static/search.js` の `DICT` に追記します

## 手元での動作確認（ネット接続なし）

サンプルデータ（架空の論文12本）で、全工程を試せます。

```bash
pip install -r requirements.txt pytest
python tests/fixtures/build_fixtures.py
python -m pipeline.run --offline tests/fixtures --data-dir /tmp/demo
python web/build.py --data-dir /tmp/demo --today 2026-10-31 --out /tmp/demo-site
python -m http.server -d /tmp/demo-site 8000   # http://localhost:8000 を開く
python -m pytest -q
```

## ファイル構成

```
config.yaml              設定（取得範囲・タグ・重み）
pipeline/                収集と加工
  arxiv.py               arXiv API（3秒に1回以下）
  s2.py                  Semantic Scholar（TLDR・引用数・採択先）
  hf.py                  Hugging Face Daily Papers（票・コード・AI要約）
  llm.py                 Gemini（OpenAI互換API）で日本語化・タグ付け
  deepl.py               予備の翻訳
  badges.py              根拠バッジの判定
  run.py                 毎日の処理の入口
web/                     静的サイトの生成（build.py・テンプレート・CSS・検索）
data/papers/YYYY-MM.json 収集したデータ（Actionsが自動でコミット）
.github/workflows/daily.yml
```

## うまく動かないとき

| 症状 | 確認すること |
|---|---|
| Actions のデータ保存で `permission denied` | Settings → Actions → General → Workflow permissions を **Read and write** にする |
| 要約がすべて「日本語化を待っています」 | `GEMINI_API_KEY` が登録されているか。Actions のログに `LLM` で始まる行があるか |
| `利用できるモデルが見つかりません` | Variable の `GEMINI_MODEL` に、AI Studio に表示されているモデル名を指定する |
| Semantic Scholar で 429 が続く | `S2_API_KEY` を登録する（なくても他の処理は続きます） |

## データの出典と規約

- arXiv：メタデータは CC0。API の規約（3秒に1リクエスト）に従っています。<https://info.arxiv.org/help/api/tou.html>
- Semantic Scholar：<https://www.semanticscholar.org/product/api/license>
- Hugging Face Papers：<https://huggingface.co/papers>

このサイトは arXiv、Semantic Scholar、Hugging Face とは関係ありません。要約はAIによるもので、誤りを含むことがあります。
