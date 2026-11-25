/* Page logic for the experience slider.  All model maths is in model.js (GFModel). */
(function () {
  "use strict";

  var M = window.GFModel;
  var K_AGENTS = 1000; // simulated learners behind every curve
  var SEED = 20261016; // seed of the simulated coin flips (same flips every time)
  var SHOWN_LEN = 8; // longest streak shown
  var SWEEP_NS = [0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 125, 150, 200, 250, 300];
  var PATH_LEN = 300; // flips drawn per learner; equals the slider and comparison maximum
  var POST_NS = [0, 1, 2, 3, 4];
  for (var q = 5; q <= 400; q += 5) POST_NS.push(q);
  var EXAMPLE_SEED_DEFAULT = 330;

  var $ = function (id) {
    return document.getElementById(id);
  };
  var SVGNS = "http://www.w3.org/2000/svg";

  function el(name, attrs, text) {
    var e = document.createElementNS(SVGNS, name);
    if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function pct(x, d) {
    return (x * 100).toFixed(d === undefined ? 1 : d) + "%";
  }

  /* ---------------- state ---------------- */
  var state = {
    n: 40,
    shown: "streak",
    cmpA: 10,
    cmpB: 100,
    wSwi: 1,
    wSte: 1,
    wSti: 1,
    steps: 4,
    degree: 90,
    mixture: false,
  };

  function clampInt(v, lo, hi, fallback) {
    var x = parseInt(v, 10);
    if (isNaN(x)) return fallback;
    return Math.max(lo, Math.min(hi, x));
  }

  function spaceOpts() {
    var wSwi = state.wSwi;
    var wSte = state.wSte;
    var wSti = state.wSti;
    var total = wSwi + wSte + wSti;
    if (total === 0) {
      wSwi = wSte = wSti = 1;
      total = 3;
    }
    var side = wSwi + wSti;
    return {
      pSteady: wSte / total,
      switchyShare: side === 0 ? 0.5 : wSwi / side,
      steps: state.steps,
      degree: state.degree / 100,
      speedMixture: state.mixture,
    };
  }

  function priorText() {
    var o = spaceOpts();
    var pSwi = (1 - o.pSteady) * o.switchyShare;
    var pSti = (1 - o.pSteady) * (1 - o.switchyShare);
    return "Switchy " + pct(pSwi) + ", Steady " + pct(o.pSteady) + ", Sticky " + pct(pSti);
  }

  /* ---------------- computation ---------------- */
  var cache = { key: null, sweep: null, post: null };
  var token = 0;

  function configKey() {
    return JSON.stringify([spaceOpts(), state.shown]);
  }

  function computeMain() {
    var space = M.buildSpace(spaceOpts());
    var ns = [];
    [state.cmpA, state.n, state.cmpB].forEach(function (n) {
      if (ns.indexOf(n) < 0) ns.push(n);
    });
    var rows = M.runAgents(space, ns, K_AGENTS, SEED, state.shown, SHOWN_LEN, PATH_LEN);
    var byN = {};
    rows.forEach(function (r) {
      byN[r.n] = r;
    });
    return byN;
  }

  function computeSweep() {
    var space = M.buildSpace(spaceOpts());
    return M.runAgents(space, SWEEP_NS, K_AGENTS, SEED, state.shown, SHOWN_LEN);
  }

  function computePost() {
    var space = M.buildSpace(spaceOpts());
    return M.runAgents(space, POST_NS, K_AGENTS, SEED, null, SHOWN_LEN);
  }

  /* ---------------- chart helper ---------------- */
  function niceRange(lo, hi, includeHalf) {
    if (includeHalf) {
      lo = Math.min(lo, 0.5);
      hi = Math.max(hi, 0.5);
    }
    lo = Math.floor((lo - 0.01) * 20) / 20;
    hi = Math.ceil((hi + 0.01) * 20) / 20;
    if (hi - lo < 0.15) {
      var mid = (hi + lo) / 2;
      lo = Math.floor((mid - 0.075) * 20) / 20;
      hi = lo + 0.15;
    }
    return [Math.max(0, lo), Math.min(1, hi)];
  }

  function yTicks(lo, hi) {
    var step = hi - lo <= 0.3 ? 0.05 : hi - lo <= 0.6 ? 0.1 : 0.2;
    var out = [];
    for (var v = Math.ceil(lo / step - 1e-9) * step; v <= hi + 1e-9; v += step) out.push(Math.round(v * 100) / 100);
    return out;
  }

  function drawChart(svg, tip, o) {
    var holder = svg.parentNode;
    var w = Math.max(280, Math.floor(holder.clientWidth - 8));
    var h = Math.round(Math.min(400, Math.max(250, w * 0.58)));
    var m = { l: 54, r: o.rightMargin || 76, t: 12, b: 48 };
    var pw = w - m.l - m.r;
    var ph = h - m.t - m.b;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute("width", w);
    svg.setAttribute("height", h);
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    var x0 = o.xdomain[0];
    var x1 = o.xdomain[1];
    var y0 = o.ydomain[0];
    var y1 = o.ydomain[1];
    var X = function (x) {
      return m.l + ((x - x0) / (x1 - x0)) * pw;
    };
    var Y = function (y) {
      return m.t + (1 - (y - y0) / (y1 - y0)) * ph;
    };

    // shaded region below 50%
    if (o.band && 0.5 > y0 && 0.5 < y1) {
      svg.appendChild(
        el("rect", { x: m.l, y: Y(0.5), width: pw, height: m.t + ph - Y(0.5), fill: "var(--band)" })
      );
    }
    // grid and ticks
    o.yticks.forEach(function (t) {
      svg.appendChild(el("line", { class: "grid", x1: m.l, x2: m.l + pw, y1: Y(t), y2: Y(t) }));
      svg.appendChild(el("text", { x: m.l - 6, y: Y(t) + 4, "text-anchor": "end" }, o.yfmt(t)));
    });
    o.xticks.forEach(function (t) {
      svg.appendChild(el("line", { class: "grid", x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph }));
      svg.appendChild(el("text", { x: X(t), y: m.t + ph + 16, "text-anchor": "middle" }, String(t)));
    });
    svg.appendChild(el("line", { class: "axis", x1: m.l, x2: m.l + pw, y1: m.t + ph, y2: m.t + ph }));
    svg.appendChild(el("line", { class: "axis", x1: m.l, x2: m.l, y1: m.t, y2: m.t + ph }));
    svg.appendChild(el("text", { class: "strong", x: m.l + pw / 2, y: h - 6, "text-anchor": "middle" }, o.xlabel));
    var yl = el("text", { class: "strong", transform: "translate(11 " + (m.t + ph / 2) + ") rotate(-90)", "text-anchor": "middle" }, o.ylabel);
    svg.appendChild(yl);
    if (o.refY !== undefined && o.refY > y0 && o.refY < y1) {
      svg.appendChild(el("line", { class: "ref", x1: m.l, x2: m.l + pw, y1: Y(o.refY), y2: Y(o.refY) }));
    }
    if (o.vline !== undefined && o.vline >= x0 && o.vline <= x1) {
      svg.appendChild(el("line", { x1: X(o.vline), x2: X(o.vline), y1: m.t, y2: m.t + ph, stroke: "var(--c-ref)", "stroke-width": 1.5, "stroke-dasharray": "5 3" }));
      svg.appendChild(el("text", { x: X(o.vline) + 4, y: m.t + 11 }, o.vlabel || ""));
    }

    // series
    var labels = [];
    o.series.forEach(function (s) {
      var d = s.points
        .map(function (p, i) {
          return (i ? "L" : "M") + X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1);
        })
        .join(" ");
      var attrs = {
        d: d,
        fill: "none",
        stroke: s.color,
        "stroke-width": s.width || 2,
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
      };
      if (s.dash) attrs["stroke-dasharray"] = s.dash;
      if (s.opacity) attrs.opacity = s.opacity;
      svg.appendChild(el("path", attrs));
      if (s.markers) {
        s.points.forEach(function (p) {
          svg.appendChild(el("circle", { cx: X(p[0]), cy: Y(p[1]), r: s.width > 2.5 ? 4 : 3, fill: s.color, stroke: "var(--surface)", "stroke-width": 1.5, opacity: s.opacity || 1 }));
        });
      }
      if (s.label) {
        var last = s.points[s.points.length - 1];
        labels.push({ y: Y(last[1]), x: X(last[0]) + 8, text: s.label, strong: s.strongLabel });
      }
    });
    // extra markers (paper's numbers)
    (o.marks || []).forEach(function (mk) {
      svg.appendChild(el("circle", { cx: X(mk.x), cy: Y(mk.y), r: 5.5, fill: "var(--surface)", stroke: mk.color, "stroke-width": 2 }));
    });
    // direct labels with simple collision avoidance
    labels.sort(function (a, b) {
      return a.y - b.y;
    });
    for (var i = 1; i < labels.length; i++) {
      if (labels[i].y - labels[i - 1].y < 14) labels[i].y = labels[i - 1].y + 14;
    }
    if (labels.length && labels[labels.length - 1].y > m.t + ph - 4) {
      labels[labels.length - 1].y = m.t + ph - 4;
      for (var j = labels.length - 2; j >= 0; j--) {
        if (labels[j + 1].y - labels[j].y < 14) labels[j].y = labels[j + 1].y - 14;
      }
    }
    labels.forEach(function (l) {
      svg.appendChild(el("text", { class: l.strong ? "strong" : "", x: l.x, y: l.y + 4 }, l.text));
    });

    // hover: nearest x of the first series
    var cursor = el("line", { class: "cursor", y1: m.t, y2: m.t + ph, visibility: "hidden" });
    svg.appendChild(cursor);
    var xs = o.series.length ? o.series[0].points.map(function (p) { return p[0]; }) : [];
    function show(evt) {
      var rect = svg.getBoundingClientRect();
      var px = evt.clientX - rect.left;
      var best = 0;
      var bd = Infinity;
      xs.forEach(function (x, i) {
        var dd = Math.abs(X(x) - px);
        if (dd < bd) {
          bd = dd;
          best = i;
        }
      });
      var xv = xs[best];
      cursor.setAttribute("x1", X(xv));
      cursor.setAttribute("x2", X(xv));
      cursor.setAttribute("visibility", "visible");
      var lines = ["<strong>" + o.tipTitle(xv) + "</strong>"];
      o.series.forEach(function (s) {
        var p = s.points[best];
        if (p) lines.push(s.tipLabel + ": " + o.tipFmt(p[1]));
      });
      tip.innerHTML = lines.join("<br>");
      tip.hidden = false;
      var tx = X(xv) + 12;
      var tw = tip.offsetWidth;
      if (tx + tw > w - 4) tx = X(xv) - tw - 12;
      tip.style.left = Math.max(4, tx) + "px";
      tip.style.top = m.t + 8 + "px";
    }
    function hide() {
      cursor.setAttribute("visibility", "hidden");
      tip.hidden = true;
    }
    svg.onpointermove = show;
    svg.onpointerdown = show;
    svg.onpointerleave = hide;
    svg.onpointercancel = hide;
  }

  function legendHtml(items) {
    return items
      .map(function (it) {
        var dash = it.dash ? ' stroke-dasharray="' + it.dash + '"' : "";
        var op = it.opacity ? ' opacity="' + it.opacity + '"' : "";
        return (
          '<span><svg viewBox="0 0 30 10" aria-hidden="true"><line x1="1" y1="5" x2="29" y2="5" stroke="' +
          it.color +
          '" stroke-width="' +
          (it.width || 2.5) +
          '" stroke-linecap="round"' +
          dash +
          op +
          "/></svg>" +
          it.text +
          "</span>"
        );
      })
      .join("");
  }

  /* ---------------- rendering ---------------- */
  var last = { main: null };

  function rowStats(row) {
    var p = row.pcont;
    var lowest = 0;
    for (var i = 1; i < p.length; i++) if (p[i] < p[lowest]) lowest = i;
    return {
      lowest: p[lowest],
      lowestAt: lowest + 1,
      cross: M.crossingStreak(p),
      at8: p[p.length - 1],
      share4: row.share_above[3],
    };
  }

  function describeRow(n, row) {
    var st = rowStats(row);
    var crossTxt = st.cross === null ? "never expects a continuation within 8 in a row" : st.cross === 1 ? "already expects a continuation after 1" : "first expects a continuation at " + st.cross + " in a row";
    return n + " outcomes seen: " + crossTxt + "; after 8 in a row it gives " + pct(st.at8) + " to another one.";
  }

  function renderMain() {
    var byN = last.main;
    if (!byN) return;
    var ns = Object.keys(byN)
      .map(Number)
      .sort(function (a, b) {
        return a - b;
      });
    var series = [];
    ns.forEach(function (n) {
      var isSel = n === state.n;
      var row = byN[n];
      series.push({
        points: row.pcont.map(function (v, i) {
          return [i + 1, v];
        }),
        color: isSel ? "var(--c-learner)" : "var(--c-ref)",
        width: isSel ? 3 : 2,
        dash: isSel ? null : n === state.cmpA ? "7 4" : "2 4",
        markers: isSel,
        label: n + " seen",
        strongLabel: isSel,
        tipLabel: n + " outcomes seen",
        sortKey: isSel ? 1 : 0,
      });
    });
    series.sort(function (a, b) {
      return a.sortKey - b.sortKey;
    });
    // the hover snaps to the first series, which is fine because all share x = 1..8
    var vals = [];
    series.forEach(function (s) {
      s.points.forEach(function (p) {
        vals.push(p[1]);
      });
    });
    var yr = niceRange(Math.min.apply(null, vals), Math.max.apply(null, vals), true);
    drawChart($("chart1"), $("tip1"), {
      xdomain: [1, SHOWN_LEN],
      ydomain: yr,
      xticks: [1, 2, 3, 4, 5, 6, 7, 8],
      yticks: yTicks(yr[0], yr[1]),
      yfmt: function (t) {
        return Math.round(t * 100) + "%";
      },
      xlabel: "Length of the streak the learner is looking at",
      ylabel: "Chance it continues",
      refY: 0.5,
      band: true,
      series: series,
      tipTitle: function (x) {
        return "Streak of " + x;
      },
      tipFmt: function (v) {
        return pct(v);
      },
    });
    $("legend1").innerHTML = legendHtml([
      { color: "var(--c-learner)", text: "experience set above", width: 3 },
      { color: "var(--c-ref)", text: "comparison amounts", dash: "7 4", width: 2 },
      { color: "var(--ink-2)", text: "50%: the outcomes are independent", dash: "2 4", width: 1.5 },
    ]);

    // summary sentence and tables
    var sel = byN[state.n];
    var st = rowStats(sel);
    var sentence;
    if (st.cross === null) sentence = "With " + state.n + " outcomes seen, the average learner never expects a streak of up to 8 to continue. Its lowest expectation is " + pct(st.lowest) + " (at a streak of " + st.lowestAt + ") and after 8 in a row it gives " + pct(st.at8) + " to another one.";
    else if (st.cross === 1) sentence = "With " + state.n + " outcomes seen, the average learner already expects a continuation after a streak of 1. After 8 in a row it gives " + pct(st.at8) + " to another one.";
    else sentence = "With " + state.n + " outcomes seen, the average learner expects a switch after short streaks (as low as " + pct(st.lowest) + " at a streak of " + st.lowestAt + ") and first expects a continuation at " + st.cross + " in a row. After 8 in a row it gives " + pct(st.at8) + " to another one.";
    var others = ns.filter(function (n) {
      return n !== state.n;
    });
    if (others.length) sentence += " For comparison: " + others.map(function (n) { return describeRow(n, byN[n]); }).join(" ");
    $("summary").textContent = sentence;
    $("chart1").setAttribute("aria-label", "Line chart. " + sentence);

    var tb = $("summary-table").querySelector("tbody");
    tb.innerHTML = "";
    ns.forEach(function (n) {
      var s2 = rowStats(byN[n]);
      var tr = document.createElement("tr");
      var cells = [
        n + (n === state.n ? " (set above)" : ""),
        pct(s2.lowest) + " at " + s2.lowestAt,
        s2.cross === null ? "none up to 8" : String(s2.cross),
        pct(s2.at8),
        s2.share4 === null ? "n/a" : pct(s2.share4, 0),
      ];
      cells.forEach(function (c, i) {
        var td = document.createElement(i === 0 ? "th" : "td");
        if (i === 0) td.setAttribute("scope", "row");
        td.textContent = c;
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });

    var full = $("full-table");
    var html = "<thead><tr><th scope='col'>Streak length</th>";
    ns.forEach(function (n) {
      html += "<th scope='col'>" + n + " seen: mean P(continue)</th><th scope='col'>" + n + " seen: learners above 50%</th>";
    });
    html += "</tr></thead><tbody>";
    for (var s = 1; s <= SHOWN_LEN; s++) {
      html += "<tr><th scope='row'>" + s + "</th>";
      ns.forEach(function (n) {
        var sh = byN[n].share_above[s - 1];
        html += "<td>" + pct(byN[n].pcont[s - 1]) + "</td><td>" + (sh === null ? "n/a" : pct(sh, 0)) + "</td>";
      });
      html += "</tr>";
    }
    html += "</tbody>";
    full.innerHTML = html;
  }

  function renderSweep() {
    if (!cache.sweep) return;
    var rows = cache.sweep;
    var picks = [
      { s: 2, opacity: 0.45, dash: "2 4", label: "streak of 2" },
      { s: 4, opacity: 0.7, dash: "7 4", label: "streak of 4" },
      { s: 8, opacity: 1, dash: null, label: "streak of 8" },
    ];
    var series = picks.map(function (p) {
      return {
        points: rows.map(function (r) {
          return [r.n, r.pcont[p.s - 1]];
        }),
        color: "var(--c-learner)",
        opacity: p.opacity,
        dash: p.dash,
        width: 2.5,
        label: p.label,
        tipLabel: p.label,
      };
    });
    var vals = [];
    series.forEach(function (s) {
      s.points.forEach(function (pt) {
        vals.push(pt[1]);
      });
    });
    var yr = niceRange(Math.min.apply(null, vals), Math.max.apply(null, vals), true);
    drawChart($("chart3"), $("tip3"), {
      xdomain: [0, 300],
      ydomain: yr,
      xticks: [0, 50, 100, 150, 200, 250, 300],
      yticks: yTicks(yr[0], yr[1]),
      yfmt: function (t) {
        return Math.round(t * 100) + "%";
      },
      xlabel: "Outcomes the learner has already seen",
      ylabel: "Chance the streak continues",
      refY: 0.5,
      band: true,
      vline: state.n,
      vlabel: "set above",
      series: series,
      tipTitle: function (x) {
        return x + " outcomes seen";
      },
      tipFmt: function (v) {
        return pct(v);
      },
      rightMargin: 84,
    });
    $("legend3").innerHTML = legendHtml([
      { color: "var(--c-learner)", opacity: 0.45, dash: "2 4", text: "streak of 2" },
      { color: "var(--c-learner)", opacity: 0.7, dash: "7 4", text: "streak of 4" },
      { color: "var(--c-learner)", text: "streak of 8" },
      { color: "var(--ink-2)", text: "50%", dash: "2 4", width: 1.5 },
    ]);
    $("chart3").setAttribute("aria-label", "Line chart of the average probability that a streak of 2, 4 or 8 continues as the learner's experience grows from 0 to 300 outcomes. Values are in the first table and its full version.");
  }

  function paperMarks() {
    var o = spaceOpts();
    var uniform = state.wSwi === state.wSte && state.wSte === state.wSti && state.wSwi > 0;
    var marks = [];
    if (!state.mixture && uniform && state.steps === 4 && state.degree === 90) {
      marks.push({ x: 20, y: 0.28, color: "var(--c-switchy)" }, { x: 20, y: 0.57, color: "var(--c-steady)" }, { x: 20, y: 0.15, color: "var(--c-sticky)" });
      marks.push({ x: 50, y: 0.13, color: "var(--c-switchy)" }, { x: 50, y: 0.84, color: "var(--c-steady)" }, { x: 50, y: 0.03, color: "var(--c-sticky)" });
      return { marks: marks, text: "Hollow circles: the values printed in the paper's Section 4 (20 and 50 outcomes)." };
    }
    if (state.mixture && state.wSwi === state.wSti && state.wSte * 10 === state.wSwi && state.degree === 90 && o.pSteady > 0) {
      marks.push({ x: 250, y: 0.17, color: "var(--c-switchy)" }, { x: 400, y: 0.08, color: "var(--c-switchy)" });
      return { marks: marks, text: "Hollow circles: the Switchy values printed in the paper's Section 4 (about 17% after 250 outcomes, 8% after 400)." };
    }
    return { marks: [], text: "" };
  }

  function renderPost() {
    if (!cache.post) return;
    var rows = cache.post;
    var mk = paperMarks();
    var defs = [
      { key: "switchy", label: "Switchy", color: "var(--c-switchy)", dash: "7 4" },
      { key: "steady", label: "Steady", color: "var(--c-steady)", dash: null },
      { key: "sticky", label: "Sticky", color: "var(--c-sticky)", dash: "1.5 4" },
    ];
    var series = defs.map(function (d) {
      return {
        points: rows.map(function (r) {
          return [r.n, r.class_post[d.key]];
        }),
        color: d.color,
        dash: d.dash,
        width: 2.5,
        label: d.label,
        tipLabel: d.label,
      };
    });
    drawChart($("chart2"), $("tip2"), {
      xdomain: [0, 400],
      ydomain: [0, 1],
      xticks: [0, 100, 200, 300, 400],
      yticks: [0, 0.2, 0.4, 0.6, 0.8, 1],
      yfmt: function (t) {
        return Math.round(t * 100) + "%";
      },
      xlabel: "Outcomes the learner has already seen",
      ylabel: "Mean belief in each kind of process",
      vline: state.n,
      vlabel: "set above",
      series: series,
      marks: mk.marks,
      tipTitle: function (x) {
        return x + " outcomes seen";
      },
      tipFmt: function (v) {
        return pct(v);
      },
      rightMargin: 64,
    });
    $("legend2").innerHTML =
      legendHtml([
        { color: "var(--c-switchy)", dash: "7 4", text: "Switchy" },
        { color: "var(--c-steady)", text: "Steady" },
        { color: "var(--c-sticky)", dash: "1.5 4", text: "Sticky" },
      ]) + (mk.text ? "<span>" + mk.text + "</span>" : "");
    $("chart2").setAttribute("aria-label", "Line chart of the mean posterior probability of Switchy, Steady and Sticky as the learner's experience grows from 0 to 400 outcomes.");
  }

  /* ---------------- worked example (paper defaults, independent of the controls) ---------------- */
  var exSeed = EXAMPLE_SEED_DEFAULT;

  function renderExample() {
    var space = M.buildSpace({});
    var flips = M.steadySequence(exSeed, 40);
    var shown = [0, 1, 1, 1, 1, 1];
    var a = M.predictAfter(space, flips.slice(0, 10), shown);
    var b = M.predictAfter(space, flips, shown);
    function letters(arr) {
      return arr
        .map(function (x) {
          return x ? "H" : "T";
        })
        .join("");
    }
    $("ex-flips").innerHTML =
      "A and B both saw: " + letters(flips.slice(0, 10)) + "<br>Only B also saw: " + letters(flips.slice(10)) + '<br>Both then see: <span class="streak">' + letters(shown) + "</span>";
    $("ex-seed").textContent = "Simulated coin number " + exSeed + ".";
    var tb = $("ex-table").querySelector("tbody");
    tb.innerHTML = "";
    function row(who, what, c) {
      var tr = document.createElement("tr");
      [who, what, pct(c.switchy), pct(c.steady), pct(c.sticky)].forEach(function (t, i) {
        var td = document.createElement(i < 2 ? "th" : "td");
        if (i < 2) td.setAttribute("scope", "row");
        td.textContent = t;
        td.style.textAlign = i < 2 ? "left" : "right";
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    }
    var prior = { switchy: space.prior[0], steady: space.prior[1], sticky: space.prior[2] };
    row("A (10 seen)", "before anything", prior);
    row("A (10 seen)", "after its 10 flips", a.after_experience_classes);
    row("A (10 seen)", "after the streak", a.after_shown_classes);
    row("B (40 seen)", "after its 40 flips", b.after_experience_classes);
    row("B (40 seen)", "after the streak", b.after_shown_classes);
    var pS = M.pContinue(space.chains[0], 5);
    var pT = M.pContinue(space.chains[2], 5);
    $("ex-text").innerHTML =
      "After 5 hits in a row a Switchy process continues with probability " + pct(pS, 0) + ", a Steady one with 50% and a Sticky one with " + pct(pT, 0) + ". Learner A therefore gives " + pct(a.p_continue, 1) +
      " to another H (" + pct(a.after_shown_classes.switchy, 1) + " &times; " + pct(pS, 0) + " + " + pct(a.after_shown_classes.steady, 1) + " &times; 50% + " + pct(a.after_shown_classes.sticky, 1) + " &times; " + pct(pT, 0) +
      "). Learner B gives " + pct(b.p_continue, 1) + ". A single pair need not follow the average pattern in Figure 1; a different simulated coin may show it more or less clearly.";
  }

  /* ---------------- wiring ---------------- */
  var pending = null;
  var needHeavy = false; // a prior/option change is waiting for the next frame
  var heavyRunning = false; // the sweep and posterior charts are being recomputed

  // document.body[data-busy] is "1" from the moment an input changes until every chart shows the
  // new state, and "0" otherwise.  It is set synchronously in the event handler, so a script
  // (the Playwright tests) that waits for "0" after an action cannot see a stale "idle" state.
  function setBusy(on) {
    document.body.setAttribute("data-busy", on ? "1" : "0");
    if (!on) window.__gfRenderCount = (window.__gfRenderCount || 0) + 1;
  }

  function recomputeAll() {
    var myToken = ++token;
    heavyRunning = true;
    $("prior-text").textContent = priorText();
    last.main = computeMain();
    renderMain();
    var key = configKey();
    if (cache.key === key && cache.sweep && cache.post) {
      renderSweep();
      renderPost();
      $("status").textContent = "";
      heavyRunning = false;
      if (!pending) setBusy(false);
      return;
    }
    $("status").textContent = "Updating the other charts\u2026";
    setTimeout(function () {
      if (myToken !== token) return;
      cache.sweep = computeSweep();
      renderSweep();
      setTimeout(function () {
        if (myToken !== token) return;
        cache.post = computePost();
        cache.key = key;
        renderPost();
        $("status").textContent = "";
        heavyRunning = false;
        if (!pending) setBusy(false);
      }, 0);
    }, 0);
  }

  function lightUpdate() {
    // only the experience slider moved: the main curves and the markers change
    $("n-out").textContent = String(state.n);
    last.main = computeMain();
    renderMain();
    if (cache.sweep) renderSweep();
    if (cache.post) renderPost();
    if (!heavyRunning && !pending) setBusy(false);
  }

  function schedule(fn) {
    setBusy(true);
    if (fn === recomputeAll) needHeavy = true;
    if (pending) cancelAnimationFrame(pending);
    pending = requestAnimationFrame(function () {
      pending = null;
      var heavy = needHeavy;
      needHeavy = false;
      if (heavy) recomputeAll();
      else lightUpdate();
    });
  }

  function setN(v) {
    state.n = clampInt(v, 0, 300, state.n);
    $("n-slider").value = state.n;
    $("n-number").value = state.n;
    schedule(lightUpdate);
  }

  function syncOutputs() {
    $("n-out").textContent = String(state.n);
    $("w-swi-out").textContent = String(state.wSwi);
    $("w-ste-out").textContent = String(state.wSte);
    $("w-sti-out").textContent = String(state.wSti);
    $("steps-out").textContent = String(state.steps);
    $("degree-out").textContent = state.degree + "%";
    $("prior-text").textContent = priorText();
    $("steps").disabled = state.mixture;
  }

  function setControlsFromState() {
    $("n-slider").value = state.n;
    $("n-number").value = state.n;
    $("cmp-a").value = state.cmpA;
    $("cmp-b").value = state.cmpB;
    $("shown").value = state.shown;
    $("w-swi").value = state.wSwi;
    $("w-ste").value = state.wSte;
    $("w-sti").value = state.wSti;
    $("steps").value = state.steps;
    $("degree").value = state.degree;
    $("mixture").checked = state.mixture;
    syncOutputs();
  }

  function init() {
    $("n-slider").addEventListener("input", function (e) {
      setN(e.target.value);
    });
    $("n-number").addEventListener("input", function (e) {
      if (e.target.value === "") return;
      setN(e.target.value);
    });
    Array.prototype.forEach.call(document.querySelectorAll("button[data-n]"), function (b) {
      b.addEventListener("click", function () {
        setN(b.getAttribute("data-n"));
      });
    });
    function bindCmp(id, key) {
      $(id).addEventListener("input", function (e) {
        if (e.target.value === "") return;
        state[key] = clampInt(e.target.value, 0, 300, state[key]);
        schedule(lightUpdate);
      });
    }
    bindCmp("cmp-a", "cmpA");
    bindCmp("cmp-b", "cmpB");
    $("shown").addEventListener("change", function (e) {
      state.shown = e.target.value;
      schedule(recomputeAll);
    });
    function bindRange(id, key) {
      $(id).addEventListener("input", function (e) {
        state[key] = parseInt(e.target.value, 10);
        syncOutputs();
        schedule(recomputeAll);
      });
    }
    bindRange("w-swi", "wSwi");
    bindRange("w-ste", "wSte");
    bindRange("w-sti", "wSti");
    bindRange("steps", "steps");
    bindRange("degree", "degree");
    $("mixture").addEventListener("change", function (e) {
      state.mixture = e.target.checked;
      syncOutputs();
      schedule(recomputeAll);
    });
    $("preset-default").addEventListener("click", function () {
      state.wSwi = state.wSte = state.wSti = 1;
      state.steps = 4;
      state.degree = 90;
      state.mixture = false;
      setControlsFromState();
      schedule(recomputeAll);
    });
    $("preset-mixture").addEventListener("click", function () {
      state.wSwi = 10;
      state.wSte = 1;
      state.wSti = 10;
      state.degree = 90;
      state.mixture = true;
      setControlsFromState();
      schedule(recomputeAll);
    });
    $("ex-new").addEventListener("click", function () {
      exSeed += 1;
      renderExample();
    });
    var rt = null;
    window.addEventListener("resize", function () {
      clearTimeout(rt);
      rt = setTimeout(function () {
        renderMain();
        renderSweep();
        renderPost();
      }, 120);
    });
    setControlsFromState();
    renderExample();
    recomputeAll();
    window.__gfReady = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
