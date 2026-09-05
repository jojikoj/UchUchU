/* UchUchU — フロントエンド挙動（依存なし・軽量） */
(function () {
  "use strict";

  // --- モバイルナビ ---
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("sidebar");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    // サイドバー外をクリックしたら閉じる
    document.addEventListener("click", function (e) {
      if (!nav.classList.contains("open")) return;
      if (nav.contains(e.target) || toggle.contains(e.target)) return;
      nav.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    });
  }

  // --- 打ち上げライブカウントダウン ---
  var counters = Array.prototype.slice.call(document.querySelectorAll(".net-countdown[data-net]"));
  if (counters.length) {
    var lang = document.body.getAttribute("data-lang") || "en";
    function pad(n) { return n < 10 ? "0" + n : "" + n; }
    function render() {
      var now = Date.now();
      counters.forEach(function (el) {
        var net = Date.parse(el.getAttribute("data-net"));
        if (isNaN(net)) return;
        var s = Math.floor((net - now) / 1000);
        if (s <= 0) {
          // 予定時刻を過ぎた直後の6時間だけ「まもなく」。
          // それ以降は元データの更新漏れなので、何も出さない。
          if (-s <= 6 * 3600) {
            el.textContent = lang === "ja" ? "まもなく" : "T-0";
          } else {
            el.textContent = "";
            el.classList.add("is-stale");
          }
          return;
        }
        var d = Math.floor(s / 86400); s -= d * 86400;
        var h = Math.floor(s / 3600); s -= h * 3600;
        var m = Math.floor(s / 60); var sec = s - m * 60;
        if (d > 0) {
          el.textContent = lang === "ja"
            ? "T-" + d + "日 " + h + "時間 " + pad(m) + "分"
            : "T-" + d + "d " + pad(h) + "h " + pad(m) + "m";
        } else {
          el.textContent = "T-" + pad(h) + ":" + pad(m) + ":" + pad(sec);
        }
      });
    }
    render();
    setInterval(render, 1000);
  }

  // --- 企業DBの絞り込み ---
  // サプライヤーを探す側が「関東で推進系」のように絞れないと、DBは名簿でしかない。
  // 54社なのでページを増やさず、この場で絞る（JSが無効でも一覧はそのまま出る）。
  var cf = document.querySelector("[data-company-filter]");
  if (cf) {
    var cards = Array.prototype.slice.call(document.querySelectorAll(".company-card[data-text]"));
    var qEl = cf.querySelector("[data-cf-q]");
    var resEl = cf.querySelector("[data-cf-result]");
    var areaBtns = Array.prototype.slice.call(cf.querySelectorAll("[data-cf-area]"));
    var area = "";

    function apply() {
      var q = (qEl && qEl.value || "").trim().toLowerCase();
      var hit = 0;
      cards.forEach(function (el) {
        var okArea = !area || el.getAttribute("data-area") === area;
        var okText = !q || (el.getAttribute("data-text") || "").indexOf(q) !== -1;
        var show = okArea && okText;
        el.hidden = !show;
        if (show) hit++;
      });
      if (!resEl) return;
      if (!q && !area) { resEl.hidden = true; return; }
      resEl.hidden = false;
      resEl.textContent = hit
        ? (resEl.getAttribute("data-hit") || "{n}").replace("{n}", hit)
        : (resEl.getAttribute("data-none") || "");
    }

    if (qEl) qEl.addEventListener("input", apply);
    areaBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        area = b.getAttribute("data-cf-area") || "";
        areaBtns.forEach(function (x) { x.classList.remove("on"); });
        b.classList.add("on");
        apply();
      });
    });
  }

  // --- 言語スイッチ: 手動で選んだ言語を記憶し、以後は自動振り分けしない ---
  var langLinks = document.querySelectorAll(".lang-switch a[hreflang]");
  Array.prototype.forEach.call(langLinks, function (a) {
    a.addEventListener("click", function () {
      try { localStorage.setItem("uchuchu-lang", a.getAttribute("hreflang")); } catch (e) {}
    });
  });
})();
