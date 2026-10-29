/*
  race-tool.js: the live split tool, the 2024 holdout charts and the per-year
  decay small multiples. Used by index.html and overview/index.html.
  Reads model/pace_model.json (train_model.py), tables/model_eval.json and
  tables/years_decay.json. The prediction code mirrors pace_model.py line for
  line; train_model.py checks the Python side against its own vectorized path.
  Set data-base on the script tag to the path of the repo root ("" or "../").
*/
(function () {
  "use strict";
  var me = document.currentScript, BASE = (me && me.getAttribute("data-base")) || "";
  var NS = "http://www.w3.org/2000/svg", FULL = 42.195, HALF = 21.0975;
  var MARKS = [[5, "5 km"], [10, "10 km"], [15, "15 km"], [20, "20 km"], [HALF, "Half"], [25, "25 km"], [30, "30 km"], [35, "35 km"], [40, "40 km"]];
  var TSEG = [[0, 5], [5, 10], [10, 20], [20, 25], [25, 30], [30, 35], [35, 40], [40, FULL]];

  function el(tag, at, parent, txt) { var e = document.createElementNS(NS, tag); for (var k in at) e.setAttribute(k, at[k]); if (txt != null) e.textContent = txt; if (parent) parent.appendChild(e); return e; }
  function $(id) { return document.getElementById(id); }
  function hms(m) { var s = Math.round(m * 60), h = Math.floor(s / 3600), mm = Math.floor(s % 3600 / 60), ss = s % 60; return h + ":" + (mm < 10 ? "0" : "") + mm + ":" + (ss < 10 ? "0" : "") + ss; }
  function hm(m) { var s = Math.round(m), h = Math.floor(s / 60), mm = s % 60; return h + ":" + (mm < 10 ? "0" : "") + mm; }
  function mmss(m) { var s = Math.round(m * 60); return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + s % 60; }
  function kmName(c) { return c === HALF ? "the half" : c + " km"; }
  function fmt(n) { return n.toLocaleString("en-US"); }
  function width(box) { return Math.max(290, box.clientWidth - 20); }
  function onResize(fn) { var t; window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(fn, 120); }); }
  function getJSON(p) { return fetch(BASE + p).then(function (r) { if (!r.ok) throw new Error(p + " " + r.status); return r.json(); }); }

  // ------------------------------------------------------------ model (mirrors pace_model.py)
  function interp(kms, ts, x) {
    var K = [0].concat(kms), T = [0].concat(ts);
    if (x <= K[0]) return T[0];
    for (var i = 1; i < K.length; i++) if (x <= K[i]) return T[i - 1] + (T[i] - T[i - 1]) * (x - K[i - 1]) / (K[i] - K[i - 1]);
    return T[T.length - 1];
  }
  function features(kms, ts, c, female, age) {
    var t5 = interp(kms, ts, 5), tp = interp(kms, ts, Math.max(c - 5, 0)), tc = interp(kms, ts, c);
    var avg = tc / c, start = t5 / 5, recent = (tc - tp) / (c - Math.max(c - 5, 0));
    var f = { f_avg: Math.log(avg), f_recent: Math.log(recent / avg), f_start: Math.log(start / avg) };
    f.f_avg2 = Math.pow(f.f_avg - 1.6, 2); f.f_avg_recent = (f.f_avg - 1.6) * f.f_recent; f.f_avg_start = (f.f_avg - 1.6) * f.f_start;
    if (female != null) f.female = female;
    if (age != null) { f.age10 = (age - 40) / 10; f.age10sq = f.age10 * f.age10; }
    return { f: f, tc: tc };
  }
  function dot(coef, names, f) { var y = coef[0]; for (var i = 0; i < names.length; i++) y += coef[i + 1] * f[names[i]]; return y; }
  function predict(M, kms, ts, female, age) {
    var c = kms[kms.length - 1], ck = M.checkpoints[String(c)];
    var variant = ((female != null ? "g" : "") + (age != null ? "a" : "")) || "none";
    var F = features(kms, ts, c, female, age), fm = ck.finish[variant];
    var y = dot(fm.coef, fm.features, F.f), even = F.tc * FULL / c;
    var b = 0; while (b < ck.bins.length && ck.bins[b] <= F.f.f_avg) b++;
    var q = fm.resid_q[b].map(function (r) { return even * Math.exp(y + r); });
    var wall;
    if (c >= 40) {
      var t = [10, 20, 35, 40].map(function (x) { return interp(kms, ts, x); });
      wall = (t[3] - t[2]) / 5 > 1.25 * (t[1] - t[0]) / 10 ? 1 : 0;
    } else {
      wall = 1 / (1 + Math.exp(-dot(M.checkpoints[String(c)].wall[variant].coef, fm.features, F.f)));
    }
    // pacing type: seen segment paces over the predicted mean pace, nearest centroid
    var mean = q[2] / FULL, best = 0, bd = Infinity, segs = [];
    TSEG.forEach(function (s, i) { if (s[1] <= c + 1e-9) segs.push(i); });
    M.types.centroids.forEach(function (cen, k) {
      var d = 0;
      segs.forEach(function (i) { var s = TSEG[i], p = (interp(kms, ts, s[1]) - interp(kms, ts, s[0])) / (s[1] - s[0]) / mean; d += (p - cen[i]) * (p - cen[i]) * (s[1] - s[0]); });
      if (d < bd) { bd = d; best = k; }
    });
    return { c: c, lo95: q[0], lo80: q[1], med: q[2], hi80: q[3], hi95: q[4], wall: wall, type: best };
  }

  // ------------------------------------------------------------ live tool
  function parseSplit(s) {
    s = s.trim(); if (!s) return null;
    var p = s.split(/[:.\s]+/).map(Number);
    if (p.some(isNaN) || p.length < 2 || p.length > 3) return NaN;
    return p.length === 3 ? p[0] * 60 + p[1] + p[2] / 60 : p[0] + p[1] / 60;
  }
  function tool(M, EV) {
    var box = $("race-tool"); if (!box) return;
    var names = M.types.names;
    box.innerHTML =
      '<div class="rt-head"><span>Split card</span><span>trained on ' + fmt(M.n_train) + " finishers, " + M.train_years[0] + " to " + M.train_years[M.train_years.length - 1] + '</span></div>' +
      '<div class="rt-body">' +
      '<div class="rt-grid" id="rt-grid"></div>' +
      '<div class="rt-opt"><label>Gender<select id="rt-g"><option value="">Not given</option><option value="F">Women</option><option value="M">Men</option></select></label>' +
      '<label>Age<input id="rt-a" type="text" inputmode="numeric" autocomplete="off" placeholder="optional"></label>' +
      '<button type="button" id="rt-ex">Fill an example</button><button type="button" id="rt-clr">Clear</button></div>' +
      '<p class="rt-hint" id="rt-hint">Cumulative race time at each mat, as m:ss or h:mm:ss. Fill them in order as you pass them; gaps are fine.</p>' +
      '<div class="rt-out" aria-live="polite">' +
      '<div><span class="rt-k">Predicted finish</span><b id="rt-med">&nbsp;</b><span id="rt-band" class="rt-s">&nbsp;</span></div>' +
      '<div><span class="rt-k">Wall risk</span><b id="rt-wall">&nbsp;</b><span class="rt-s">chance the 35 to 40 km pace ends up 25% slower than 10 to 20 km</span></div>' +
      '<div><span class="rt-k">Pacing type so far</span><b id="rt-type">&nbsp;</b><span id="rt-tdesc" class="rt-s">&nbsp;</span></div>' +
      '</div>' +
      '<div class="chart" id="rt-chart"></div>' +
      '<p class="readout" id="rt-read" aria-live="polite">Each column is the prediction made at that mat: thick bar 80%, thin bar 95%, dot the median. Focus the chart and use the arrow keys to read one.</p>' +
      "</div>";
    var grid = $("rt-grid");
    MARKS.forEach(function (m, i) {
      var id = "rt-m" + i;
      grid.insertAdjacentHTML("beforeend", '<label for="' + id + '">' + m[1] + '<input id="' + id + '" type="text" inputmode="numeric" autocomplete="off" spellcheck="false" placeholder="' + (m[0] < 13 ? "m:ss" : "h:mm:ss") + '"></label>');
    });
    var inputs = MARKS.map(function (m, i) { return $("rt-m" + i); }), hint = $("rt-hint");
    var steps = [], cur = -1;
    function run() {
      var kms = [], ts = [], bad = null;
      inputs.forEach(function (inp, i) {
        var v = parseSplit(inp.value); inp.classList.remove("bad");
        if (v === null) return;
        if (isNaN(v)) { bad = bad || "Couldn't read the " + MARKS[i][1] + " time."; inp.classList.add("bad"); return; }
        if (ts.length && v <= ts[ts.length - 1]) { bad = bad || "The " + MARKS[i][1] + " time has to be later than the one before it."; inp.classList.add("bad"); return; }
        var pace = v / MARKS[i][0];
        if (pace < 2.5 || pace > 20) { bad = bad || "The " + MARKS[i][1] + " time works out to " + mmss(pace) + " per km; check it."; inp.classList.add("bad"); return; }
        kms.push(MARKS[i][0]); ts.push(v);
      });
      hint.textContent = bad || "Cumulative race time at each mat, as m:ss or h:mm:ss. Fill them in order as you pass them; gaps are fine.";
      hint.className = "rt-hint" + (bad ? " warn" : "");
      var g = $("rt-g").value, female = g === "F" ? 1 : g === "M" ? 0 : null;
      var a = parseFloat($("rt-a").value), age = isFinite(a) && a >= 16 && a <= 90 ? a : null;
      steps = [];
      for (var j = 1; j <= kms.length; j++) steps.push(predict(M, kms.slice(0, j), ts.slice(0, j), female, age));
      var last = steps[steps.length - 1];
      if (!last) {
        ["rt-med", "rt-wall", "rt-type"].forEach(function (id) { $(id).innerHTML = "&nbsp;"; });
        $("rt-band").innerHTML = "Enter at least one split."; $("rt-tdesc").innerHTML = "&nbsp;";
      } else {
        $("rt-med").textContent = hms(last.med);
        $("rt-band").textContent = "80%: " + hm(last.lo80) + " to " + hm(last.hi80) + " · 95%: " + hm(last.lo95) + " to " + hm(last.hi95);
        $("rt-wall").textContent = last.c >= 40 ? (last.wall ? "Yes" : "No") : Math.round(last.wall * 100) + "%";
        $("rt-type").textContent = names[last.type];
        var mt = EV && EV.types.match_full_race_by_checkpoint[String(last.c)];
        $("rt-tdesc").textContent = M.types.shape[last.type] + (mt != null ? ". On 2024 runners, the type read at " + kmName(last.c) + " matched the full-race type " + Math.round(mt * 100) + "% of the time." : "");
      }
      cur = steps.length - 1; draw();
    }
    var svg, X, Y;
    function draw() {
      var cb = $("rt-chart"), W = width(cb), H = W < 560 ? 250 : 290, L = 52, R = 14, T = 14, B = 34;
      cb.innerHTML = "";
      var lo = Infinity, hi = -Infinity;
      steps.forEach(function (s) { lo = Math.min(lo, s.lo95); hi = Math.max(hi, s.hi95); });
      if (!steps.length) { lo = 180; hi = 270; }
      var pad = Math.max(4, (hi - lo) * 0.08); lo = Math.floor((lo - pad) / 5) * 5; hi = Math.ceil((hi + pad) / 5) * 5;
      X = function (km) { return L + km / FULL * (W - L - R); }; Y = function (m) { return T + (hi - m) / (hi - lo) * (H - T - B); };
      svg = el("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, tabindex: 0, role: "img",
        "aria-label": steps.length ? "Predicted finish band at each split entered. Latest, at " + kmName(steps[steps.length - 1].c) + ": median " + hms(steps[steps.length - 1].med) + ", 80% range " + hm(steps[steps.length - 1].lo80) + " to " + hm(steps[steps.length - 1].hi80) + "." : "Empty chart: no splits entered yet." }, cb);
      var stepv = (hi - lo) > 90 ? 30 : (hi - lo) > 40 ? 15 : (hi - lo) > 16 ? 5 : 2;
      for (var v = Math.ceil(lo / stepv) * stepv; v <= hi; v += stepv) { el("line", { class: "grid", x1: L, x2: W - R, y1: Y(v), y2: Y(v) }, svg); el("text", { x: L - 6, y: Y(v) + 4, "text-anchor": "end" }, svg, hm(v)); }
      [0, 10, 20, 30, 40].forEach(function (k) { el("text", { x: X(k), y: H - B + 18, "text-anchor": "middle" }, svg, k + (k === 40 ? " km" : "")); });
      var bw = Math.max(6, Math.min(16, (W - L - R) / 30));
      steps.forEach(function (s, i) {
        var x = X(s.c), on = i === cur;
        el("line", { class: "rt-95" + (on ? " on" : ""), x1: x, x2: x, y1: Y(s.hi95), y2: Y(s.lo95) }, svg);
        el("rect", { class: "rt-80" + (on ? " on" : ""), x: x - bw / 2, y: Y(s.hi80), width: bw, height: Math.max(1, Y(s.lo80) - Y(s.hi80)) }, svg);
        el("rect", { class: "rt-med", x: x - bw / 2 - 2, y: Y(s.med) - 1.5, width: bw + 4, height: 3 }, svg);
      });
      if (steps.length > 1) {
        var d = ""; steps.forEach(function (s, i) { d += (i ? "L" : "M") + X(s.c).toFixed(1) + " " + Y(s.med).toFixed(1); });
        el("path", { class: "rt-path", d: d }, svg);
      }
      svg.addEventListener("keydown", function (e) { if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && steps.length) { e.preventDefault(); cur = Math.max(0, Math.min(steps.length - 1, cur + (e.key === "ArrowRight" ? 1 : -1))); draw(); svg.focus(); } });
      svg.addEventListener("mousemove", function (e) {
        if (!steps.length) return; var r = svg.getBoundingClientRect(), km = ((e.clientX - r.left) * W / r.width - L) / (W - L - R) * FULL, bi = 0;
        steps.forEach(function (s, i) { if (Math.abs(s.c - km) < Math.abs(steps[bi].c - km)) bi = i; });
        if (bi !== cur) { cur = bi; draw(); }
      });
      var s = steps[cur];
      $("rt-read").textContent = s ? "At " + kmName(s.c) + ": median " + hms(s.med) + ", 80% " + hm(s.lo80) + " to " + hm(s.hi80) + " (" + Math.round(s.hi80 - s.lo80) + " min wide), 95% " + hm(s.lo95) + " to " + hm(s.hi95) + "." : "Each column is the prediction made at that mat: thick bar 80%, thin bar 95%, dot the median.";
    }
    inputs.concat([$("rt-g"), $("rt-a")]).forEach(function (i) { i.addEventListener("input", run); });
    $("rt-ex").addEventListener("click", function () {
      // a made-up runner, about 3:22 pace at the half, who slows from 25 km
      var ex = ["23:40", "47:30", "1:11:30", "1:35:50", "1:41:15", "2:02:10", "2:29:40", "2:58:30", ""];
      inputs.forEach(function (inp, i) { inp.value = ex[i]; }); run();
    });
    $("rt-clr").addEventListener("click", function () { inputs.forEach(function (inp) { inp.value = ""; }); run(); });
    onResize(draw);
    run();
  }

  // ------------------------------------------------------------ holdout charts
  function coverage(EV) {
    var box = $("calib"); if (!box) return;
    var C = EV.checkpoints, cur = 4, read = $("calib-read");
    function draw() {
      var W = width(box), H = W < 560 ? 250 : 290, L = 46, R = 14, T = 16, B = 34, y0 = 60, y1 = 100;
      var X = function (i) { return L + (i + 0.5) * (W - L - R) / C.length; }, Y = function (v) { return T + (y1 - v) / (y1 - y0) * (H - T - B); };
      box.innerHTML = "";
      var s = el("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, tabindex: 0, role: "img",
        "aria-label": "Share of 2024 finishers whose finish time fell inside the predicted interval, at each checkpoint. 80% intervals covered between " + Math.round(Math.min.apply(null, C.map(function (c) { return c.cov80; })) * 100) + " and " + Math.round(Math.max.apply(null, C.map(function (c) { return c.cov80; })) * 100) + "%; 95% intervals between " + Math.round(Math.min.apply(null, C.map(function (c) { return c.cov95; })) * 100) + " and " + Math.round(Math.max.apply(null, C.map(function (c) { return c.cov95; })) * 100) + "%." }, box);
      for (var v = y0; v <= y1; v += 10) { el("line", { class: "grid", x1: L, x2: W - R, y1: Y(v), y2: Y(v) }, s); el("text", { x: L - 6, y: Y(v) + 4, "text-anchor": "end" }, s, v + "%"); }
      C.forEach(function (c, i) { el("text", { x: X(i), y: H - B + 18, "text-anchor": "middle" }, s, c.checkpoint_km > 21 && c.checkpoint_km < 22 ? (W < 560 ? "½" : "half") : String(c.checkpoint_km)); });
      el("rect", { class: "band", id: "cband", x: X(cur) - (W - L - R) / C.length / 2, y: T, width: (W - L - R) / C.length, height: H - T - B }, s);
      [[80, "cov80", "s80"], [95, "cov95", "s95"]].forEach(function (k) {
        el("line", { class: "nom", x1: L, x2: W - R, y1: Y(k[0]), y2: Y(k[0]) }, s);
        var d = ""; C.forEach(function (c, i) { d += (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(c[k[1]] * 100).toFixed(1); });
        el("path", { class: "ln " + k[2], d: d }, s);
        C.forEach(function (c, i) { el("rect", { class: "pt " + k[2], x: X(i) - 3.5, y: Y(c[k[1]] * 100) - 3.5, width: 7, height: 7 }, s); });
      });
      el("text", { class: "lab", x: W - R - 4, y: Y(95) - 6, "text-anchor": "end" }, s, "95% target");
      el("text", { class: "lab", x: W - R - 4, y: Y(80) - 6, "text-anchor": "end" }, s, "80% target");
      s.addEventListener("keydown", function (e) { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); show(cur + (e.key === "ArrowRight" ? 1 : -1)); } });
      s.addEventListener("mousemove", function (e) { var r = s.getBoundingClientRect(); show(Math.floor(((e.clientX - r.left) * W / r.width - L) / ((W - L - R) / C.length))); });
      s.addEventListener("focus", function () { show(cur); });
      show(cur);
      function show(i) {
        cur = Math.max(0, Math.min(C.length - 1, i)); var c = C[cur], b = $("cband");
        b.setAttribute("x", X(cur) - (W - L - R) / C.length / 2);
        read.textContent = "At " + kmName(c.checkpoint_km > 21 && c.checkpoint_km < 22 ? HALF : c.checkpoint_km) + ": 80% intervals held " + (c.cov80 * 100).toFixed(1) + "% of 2024 finishers (median width " + Math.round(c.median_width80) + " min), 95% intervals held " + (c.cov95 * 100).toFixed(1) + "% (" + Math.round(c.median_width95) + " min).";
      }
    }
    onResize(draw); draw();
  }

  function maeTable(EV) {
    var tb = $("mae-body"); if (!tb) return;
    var g = {}; (EV.holdout_gbm_after_choice || []).forEach(function (r) { g[r.checkpoint_km] = r.mae_gbm; });
    tb.innerHTML = EV.checkpoints.map(function (c) {
      var k = c.checkpoint_km > 21 && c.checkpoint_km < 22 ? "Half" : c.checkpoint_km + " km";
      return "<tr><td>" + k + '</td><td class="num">' + c.mae_even.toFixed(1) + '</td><td class="num">' + c.mae_fade_rule.toFixed(1) + '</td><td class="num"><b>' + c.mae_model.toFixed(1) + '</b></td><td class="num">' + (g[c.checkpoint_km] != null ? g[c.checkpoint_km].toFixed(1) : "") + '</td><td class="num">' + (c.brier_wall != null ? c.brier_wall.toFixed(3) + " / " + c.brier_wall_base_rate.toFixed(3) : "known") + "</td></tr>";
    }).join("");
  }

  function reliability(EV) {
    var box = $("rel"); if (!box) return;
    var keys = [["10", "10 km"], ["21.0975", "Half"], ["30", "30 km"], ["35", "35 km"]], sel = 1, seg = $("rel-seg"), read = $("rel-read");
    keys.forEach(function (k, i) {
      var b = document.createElement("button"); b.type = "button"; b.textContent = k[1]; b.setAttribute("aria-pressed", i === sel ? "true" : "false");
      b.addEventListener("click", function () { sel = i; seg.querySelectorAll("button").forEach(function (o, j) { o.setAttribute("aria-pressed", j === i ? "true" : "false"); }); draw(); });
      seg.appendChild(b);
    });
    var pts = [], cur = 0;
    function draw() {
      var W = Math.min(width(box), 620), H = Math.min(Math.round(W * 0.7), 360), L = 46, R = 14, T = 14, B = 38;
      var X = function (v) { return L + v * (W - L - R); }, Y = function (v) { return T + (1 - v) * (H - T - B); };
      box.innerHTML = "";
      var rows = EV.wall.reliability[keys[sel][0]].filter(function (r) { return r.n >= 50; });
      var tot = rows.reduce(function (a, r) { return a + r.n; }, 0);
      var s = el("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, tabindex: 0, role: "img",
        "aria-label": "Wall-risk reliability at " + keys[sel][1] + " on 2024 finishers: predicted probability against the observed share, in tenths. Points on the diagonal are calibrated." }, box);
      for (var v = 0; v <= 1.001; v += 0.2) {
        el("line", { class: "grid", x1: L, x2: W - R, y1: Y(v), y2: Y(v) }, s); el("text", { x: L - 6, y: Y(v) + 4, "text-anchor": "end" }, s, Math.round(v * 100) + "%");
        el("text", { x: X(v), y: H - B + 18, "text-anchor": "middle" }, s, Math.round(v * 100) + "%");
      }
      el("text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle" }, s, "predicted wall risk");
      el("line", { class: "nom", x1: X(0), y1: Y(0), x2: X(1), y2: Y(1) }, s);
      var d = ""; rows.forEach(function (r, i) { d += (i ? "L" : "M") + X(r.mean_pred).toFixed(1) + " " + Y(r.observed).toFixed(1); });
      el("path", { class: "ln s95", d: d }, s);
      pts = rows.map(function (r) { var z = 3 + 9 * Math.sqrt(r.n / tot); return el("rect", { class: "pt s95", x: X(r.mean_pred) - z, y: Y(r.observed) - z, width: 2 * z, height: 2 * z }, s); });
      cur = Math.min(cur, rows.length - 1);
      function show(i) { cur = Math.max(0, Math.min(rows.length - 1, i)); pts.forEach(function (p, j) { p.classList.toggle("on", j === cur); }); var r = rows[cur];
        var ab = r.bin.split("-").map(function (v) { return Math.round(parseFloat(v) * 100); });
        read.textContent = keys[sel][1] + ", predicted " + ab[0] + " to " + ab[1] + "%: " + fmt(r.n) + " runners, mean prediction " + Math.round(r.mean_pred * 100) + "%, " + Math.round(r.observed * 100) + "% actually hit the wall."; }
      s.addEventListener("keydown", function (e) { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); show(cur + (e.key === "ArrowRight" ? 1 : -1)); } });
      s.addEventListener("mousemove", function (e) { var r = s.getBoundingClientRect(), x = ((e.clientX - r.left) * W / r.width - L) / (W - L - R), bi = 0;
        rows.forEach(function (q, i) { if (Math.abs(q.mean_pred - x) < Math.abs(rows[bi].mean_pred - x)) bi = i; }); show(bi); });
      s.addEventListener("focus", function () { show(cur); });
      show(cur);
    }
    onResize(draw); draw();
  }

  // ------------------------------------------------------------ per-year small multiples
  function years(YD) {
    var box = $("years"); if (!box) return;
    var SEG = YD.segments, ref = null;
    YD.years.forEach(function (y) { if (y.year === 2014) ref = y; });
    function rel(p) { return p.map(function (v) { return (v / p[1] - 1) * 100; }); }
    function draw() {
      box.innerHTML = "";
      var cols = box.clientWidth < 520 ? 2 : box.clientWidth < 820 ? 3 : 4, gap = 10;
      var W = Math.floor((box.clientWidth - 2 - gap * (cols - 1)) / cols) - 2, H = Math.round(W * 0.72), L = 30, R = 6, T = 8, B = 20, y0 = -5, y1 = 25;
      var X = function (km) { return L + km / FULL * (W - L - R); }, Y = function (v) { return T + (y1 - Math.max(y0, Math.min(y1, v))) / (y1 - y0) * (H - T - B); };
      function path(p) { var r = rel(p), d = ""; SEG.forEach(function (s, i) { d += (i ? "L" : "M") + X(s[1]).toFixed(1) + " " + Y(r[i]).toFixed(1) + "L" + X(s[2]).toFixed(1) + " " + Y(r[i]).toFixed(1); }); return d; }
      YD.years.slice().reverse().forEach(function (y) {
        var r = rel(y.pace), peak = Math.max.apply(null, r);
        var cell = document.createElement("div"); cell.className = "ym" + (y.comparable ? "" : " off"); cell.style.width = (W + 2) + "px";
        cell.innerHTML = '<p class="ym-h"><b>' + y.year + "</b> " + (y.comparable ? fmt(y.n) + " runners" : "halted race") + '</p>';
        var s = el("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, tabindex: 0, role: "img",
          "aria-label": y.year + (y.comparable ? "" : ", race halted, finishers before the stop only") + ": slowest segment " + peak.toFixed(0) + "% slower than 5 to 10 km; median late slowdown " + y.wall_median.toFixed(1) + "%, " + y.wall_over25.toFixed(0) + "% of runners more than 25% slower late." }, cell);
        [0, 10, 20].forEach(function (v) { el("line", { class: "grid", x1: L, x2: W - R, y1: Y(v), y2: Y(v) }, s); el("text", { x: L - 4, y: Y(v) + 4, "text-anchor": "end" }, s, (v ? "+" : "") + v); });
        [0, 20, 40].forEach(function (k) { el("text", { x: X(k), y: H - 5, "text-anchor": "middle" }, s, k); });
        if (y.year !== 2014) el("path", { class: "ln ref", d: path(ref.pace) }, s);
        el("path", { class: "ln " + (y.year === 2014 ? "y14" : "on"), d: path(y.pace) }, s);
        cell.insertAdjacentHTML("beforeend", '<p class="ym-f">late slowdown <b>' + y.wall_median.toFixed(1) + "%</b> · " + y.wall_over25.toFixed(0) + "% over +25%</p>");
        box.appendChild(cell);
      });
    }
    onResize(draw); draw();
  }

  function typesTable(M, EV) {
    var tb = $("types-body"); if (!tb) return;
    var T = M.types;
    tb.innerHTML = T.names.map(function (n, k) {
      return "<tr><td><b>" + n + "</b></td><td>" + T.shape[k].replace(", against the runner's own average pace", "") + '</td><td class="num">' + T.train_shares_pct[k].toFixed(0) + '%</td><td class="num">' + (EV ? EV.types.shares_pct[k].toFixed(0) + "%" : "") + "</td></tr>";
    }).join("");
  }

  function fail(ids, msg) { ids.forEach(function (id) { var b = $(id); if (b) b.innerHTML = '<p class="rt-err">' + msg + "</p>"; }); }

  var M = getJSON("model/pace_model.json"), E = getJSON("tables/model_eval.json"), Yd = getJSON("tables/years_decay.json");
  Promise.all([M, E]).then(function (r) { tool(r[0], r[1]); typesTable(r[0], r[1]); coverage(r[1]); maeTable(r[1]); reliability(r[1]); })
    .catch(function (e) { fail(["race-tool", "calib", "rel"], "The model files did not load (" + e.message + "). The tool needs the page to be served over HTTP."); });
  Yd.then(years).catch(function (e) { fail(["years"], "tables/years_decay.json did not load (" + e.message + ")."); });
})();
