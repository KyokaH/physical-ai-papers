// ブラウザ内で search.json を検索する。日本語の語は対応する英語にも広げて探す。
(function () {
  "use strict";
  var ROOT = window.SEARCH_ROOT || "../";
  // 日本語 → 英語の対応表（必要に応じて追記してください）
  var DICT = {
    "把持": ["grasp", "grasping"], "つかむ": ["grasp", "grasping"], "掴む": ["grasp", "grasping"],
    "器用": ["dexterous", "dexterity"], "多指": ["multi-fingered", "dexterous hand"], "手内": ["in-hand"],
    "操作": ["manipulation"], "マニピュレーション": ["manipulation"], "両腕": ["bimanual", "dual-arm"], "双腕": ["bimanual", "dual-arm"],
    "触覚": ["tactile", "touch"], "力覚": ["force", "haptic"],
    "ヒューマノイド": ["humanoid"], "人型": ["humanoid"], "二足": ["biped", "bipedal"], "四脚": ["quadruped"],
    "脚": ["legged", "locomotion"], "歩行": ["walking", "locomotion"], "移動": ["locomotion", "mobile"],
    "模倣学習": ["imitation learning", "behavior cloning"], "強化学習": ["reinforcement learning", "rl"],
    "世界モデル": ["world model"], "拡散": ["diffusion"], "基盤モデル": ["foundation model"],
    "言語指示": ["language instruction", "language-conditioned"], "言語": ["language"],
    "ナビゲーション": ["navigation"], "経路計画": ["path planning", "motion planning"], "計画": ["planning"],
    "自動運転": ["autonomous driving"], "シミュレーション": ["simulation", "simulator"], "実機": ["real-world", "real robot"],
    "遠隔操作": ["teleoperation"], "データセット": ["dataset"], "ベンチマーク": ["benchmark"],
    "安全": ["safety", "safe"], "協調": ["collaboration", "human-robot"], "物体認識": ["object detection", "recognition"],
    "点群": ["point cloud"], "深度": ["depth"], "姿勢推定": ["pose estimation"], "自己位置推定": ["localization", "slam"],
    "汎用": ["generalist", "general-purpose"], "スケーリング": ["scaling"], "蒸留": ["distillation"],
    "ドローン": ["drone", "uav", "aerial"], "グリッパ": ["gripper"], "ハンド": ["hand"]
  };
  var $ = function (id) { return document.getElementById(id); };
  var form = $("search-form"), resEl = $("results"), expEl = $("expanded");
  var data = null;

  function norm(s) { return (s || "").normalize("NFKC").toLowerCase(); }
  function esc(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function expand(term) {
    var out = [term];
    Object.keys(DICT).forEach(function (ja) {
      if (term.indexOf(norm(ja)) !== -1 || norm(ja).indexOf(term) !== -1 && term.length >= 2) {
        DICT[ja].forEach(function (en) { if (out.indexOf(en) === -1) out.push(en); });
      }
    });
    return out;
  }
  function highlight(text, words) {
    var t = esc(text);
    words.forEach(function (w) {
      if (!w || w.length < 2) return;
      var re = new RegExp("(" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      t = t.replace(re, "<mark>$1</mark>");
    });
    return t;
  }
  function badges(p) {
    var b = [];
    if (p.a) b.push('<li class="ev ev-accepted">採択 ' + esc(p.v) + "</li>");
    if (p.c) b.push('<li class="ev ev-code">コード</li>');
    if (p.r) b.push('<li class="ev ev-real">実機評価</li>');
    if (p.n) b.push('<li class="ev">引用 ' + p.n + "</li>");
    if (p.u) b.push('<li class="ev">HF ' + p.u + "票</li>");
    return '<ul class="evidence">' + b.join("") + "</ul>";
  }
  var SRC = { "S2": "s2", "HF": "hf", "AI生成": "ai", "DeepL": "deepl" };

  function run() {
    var fd = new FormData(form);
    var q = norm(fd.get("q")).trim();
    var tag = fd.get("tag"), needA = fd.get("a"), needC = fd.get("c"), needR = fd.get("r");
    var params = new URLSearchParams();
    if (q) params.set("q", fd.get("q"));
    if (tag) params.set("tag", tag);
    ["a", "c", "r"].forEach(function (k) { if (fd.get(k)) params.set(k, "1"); });
    history.replaceState(null, "", params.toString() ? "?" + params.toString() : location.pathname);

    var terms = q ? q.split(/[\s　]+/).filter(Boolean) : [];
    var groups = terms.map(expand);
    var shown = groups.filter(function (g) { return g.length > 1; })
      .map(function (g) { return g[0] + " → " + g.slice(1).join(", "); });
    expEl.textContent = shown.length ? "英語でも探しています：" + shown.join(" / ") : "";

    if (!terms.length && !tag && !needA && !needC && !needR) {
      resEl.innerHTML = '<p class="empty">キーワードを入力するか、絞り込みを選んでください。</p>';
      return;
    }
    var hits = [];
    data.forEach(function (p) {
      if (tag && p.g.indexOf(tag) === -1) return;
      if (needA && !p.a) return;
      if (needC && !p.c) return;
      if (needR && !p.r) return;
      var jaText = norm([p.j, p.s, p.k.join(" ")].join(" "));
      var enText = norm([p.t, p.e, p.k.join(" ")].join(" "));
      var score = 0;
      for (var i = 0; i < groups.length; i++) {
        var g = groups[i], ok = false;
        for (var j = 0; j < g.length; j++) {
          var w = g[j];
          if (jaText.indexOf(w) !== -1) { ok = true; score += j === 0 ? 3 : 1; }
          if (enText.indexOf(w) !== -1) { ok = true; score += 1; }
        }
        if (!ok) return;
      }
      hits.push({ p: p, score: score });
    });
    hits.sort(function (x, y) { return y.score - x.score || (y.p.d > x.p.d ? 1 : -1); });
    var words = [].concat.apply([], groups);
    var html = '<p class="page-note">' + hits.length + "件見つかりました" + (hits.length > 200 ? "（上位200件を表示）" : "") + "</p>";
    hits.slice(0, 200).forEach(function (h) {
      var p = h.p, href = ROOT + "paper/" + encodeURIComponent(p.i) + "/index.html";
      html += '<article class="entry"><div class="entry-side"><time datetime="' + esc(p.d) + '">' + esc(p.d.replace(/-/g, "/")) + "</time></div>" +
        '<div class="entry-body"><p class="tldr"><a href="' + href + '">' + (p.s ? highlight(p.s, words) : "日本語化を待っています") + "</a></p>" +
        '<p class="titles">' + (p.src ? '<span class="src src-' + SRC[p.src] + '">' + esc(p.src) + "</span>" : "") +
        (p.j ? '<span class="title-ja">' + highlight(p.j, words) + "</span>" : "") +
        '<span class="title-en" lang="en">' + highlight(p.t, words) + "</span></p>" + badges(p) + "</div></article>";
    });
    if (!hits.length) html = '<p class="empty">見つかりませんでした。言葉を減らすか、別の言い方（例：「把持」を「つかむ」）で試してください。</p>';
    resEl.innerHTML = html;
  }

  function init() {
    var params = new URLSearchParams(location.search);
    if (params.get("q")) $("q").value = params.get("q");
    if (params.get("tag")) $("tag").value = params.get("tag");
    ["a", "c", "r"].forEach(function (k) {
      if (params.get(k)) form.querySelector('input[name="' + k + '"]').checked = true;
    });
    form.addEventListener("submit", function (e) { e.preventDefault(); run(); });
    form.addEventListener("change", run);
    run();
  }

  resEl.innerHTML = '<p class="empty">検索用データを読み込んでいます…</p>';
  fetch(ROOT + "search.json").then(function (r) {
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }).then(function (d) { data = d; init(); })
    .catch(function () { resEl.innerHTML = '<p class="empty">検索用データを読み込めませんでした。ページを再読み込みしてください。</p>'; });
})();
