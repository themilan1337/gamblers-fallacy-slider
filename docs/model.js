/*
 * JavaScript port of the causal-uncertainty model of Dorst (2026), "Bayesians Commit the
 * Gambler's Fallacy", Cognitive Science 50(1): e70171, https://doi.org/10.1111/cogs.70171
 *
 * This file mirrors src/gfmodel/model.py and src/gfmodel/experience.py function by function.
 * tests/test_crosscheck_js.py runs both on a grid of parameters and requires the outputs to agree
 * to 1e-9.  It has no dependencies and works as a plain <script> in a browser and as a CommonJS
 * module in Node.
 *
 * CHOICES the paper leaves open (same as the Python reference):
 *  - the first outcome of every sequence has probability 0.5 under every hypothesis and the
 *    streak counter starts at 1 after it; each sequence the learner sees is a fresh run of the
 *    chain;
 *  - "uniformly unsure" over x = 1..10 steps is read as uniform over the 21 chains (Steady 1/21);
 *  - the sequence shown after the experience is either one miss followed by s hits (a streak of
 *    length exactly s) or all equally likely IID sequences of 8 outcomes that end in a streak of
 *    exactly s.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.GFModel = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var HIT_RATE = 0.5;
  var DEFAULT_STEPS = 4;
  var DEFAULT_DEGREE = 0.9;
  var DEFAULT_MAX_STEPS = 10;
  var DEFAULT_SHOWN_LENGTH = 8;
  var TIE_TOLERANCE = 1e-12;
  var SWITCHY = -1;
  var STEADY = 0;
  var STICKY = 1;
  var CLASS_NAMES = { "-1": "switchy", "0": "steady", "1": "sticky" };

  /* ---- seeded generator (mulberry32), identical to experience.Mulberry32 ---- */
  function Mulberry32(seed) {
    this.state = seed | 0;
  }
  Mulberry32.prototype.random = function () {
    this.state = (this.state + 0x6d2b79f5) | 0;
    var a = this.state;
    var t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  Mulberry32.prototype.flip = function () {
    return this.random() < HIT_RATE ? 1 : 0;
  };

  function steadySequence(seed, n) {
    var rng = new Mulberry32(seed);
    var out = [];
    for (var i = 0; i < n; i++) out.push(rng.flip());
    return out;
  }

  /* ---- chains (Section 3) ---- */
  function chain(kind, steps, degree) {
    return {
      kind: kind,
      steps: steps === undefined ? DEFAULT_STEPS : steps,
      degree: degree === undefined ? DEFAULT_DEGREE : degree,
    };
  }

  function shift(c, k) {
    if (c.kind === STEADY) return 0.0;
    return ((c.degree - HIT_RATE) / c.steps) * Math.min(k, c.steps);
  }

  function pContinue(c, k) {
    return HIT_RATE + c.kind * shift(c, k);
  }

  function logLikelihood(c, seq) {
    if (seq.length === 0) return 0.0;
    var total = Math.log(HIT_RATE);
    var streak = 1;
    for (var t = 1; t < seq.length; t++) {
      var pc = pContinue(c, streak);
      if (seq[t] === seq[t - 1]) {
        total += Math.log(pc);
        streak += 1;
      } else {
        total += Math.log(1.0 - pc);
        streak = 1;
      }
    }
    return total;
  }

  function endStreak(seq) {
    if (seq.length === 0) return 0;
    var k = 1;
    for (var t = seq.length - 1; t > 0; t--) {
      if (seq[t] === seq[t - 1]) k += 1;
      else break;
    }
    return k;
  }

  /* ---- hypothesis space and prior ---- */
  function buildSpace(opts) {
    opts = opts || {};
    var pSteady = opts.pSteady === undefined ? 1.0 / 3.0 : opts.pSteady;
    var switchyShare = opts.switchyShare === undefined ? 0.5 : opts.switchyShare;
    var steps = opts.steps === undefined ? DEFAULT_STEPS : opts.steps;
    var degree = opts.degree === undefined ? DEFAULT_DEGREE : opts.degree;
    var speedMixture = !!opts.speedMixture;
    var maxSteps = opts.maxSteps === undefined ? DEFAULT_MAX_STEPS : opts.maxSteps;
    if (!(pSteady >= 0 && pSteady <= 1)) throw new Error("pSteady must be in [0, 1]");
    if (!(switchyShare >= 0 && switchyShare <= 1)) throw new Error("switchyShare must be in [0, 1]");
    var pSwi = (1.0 - pSteady) * switchyShare;
    var pSti = (1.0 - pSteady) * (1.0 - switchyShare);
    var chains = [];
    var prior = [];
    var x;
    if (speedMixture) {
      chains.push(chain(STEADY));
      prior.push(pSteady);
      for (x = 1; x <= maxSteps; x++) {
        chains.push(chain(SWITCHY, x, degree));
        prior.push(pSwi / maxSteps);
      }
      for (x = 1; x <= maxSteps; x++) {
        chains.push(chain(STICKY, x, degree));
        prior.push(pSti / maxSteps);
      }
    } else {
      chains = [chain(SWITCHY, steps, degree), chain(STEADY), chain(STICKY, steps, degree)];
      prior = [pSwi, pSteady, pSti];
    }
    return { chains: chains, prior: prior };
  }

  function posteriorFromLoglik(prior, logliks) {
    var m = -Infinity;
    var i;
    for (i = 0; i < logliks.length; i++) if (logliks[i] > m) m = logliks[i];
    var w = [];
    var z = 0.0;
    for (i = 0; i < logliks.length; i++) {
      var v = prior[i] * Math.exp(logliks[i] - m);
      w.push(v);
      z += v;
    }
    for (i = 0; i < w.length; i++) w[i] = w[i] / z;
    return w;
  }

  function posterior(space, seq) {
    var ll = space.chains.map(function (c) {
      return logLikelihood(c, seq);
    });
    return posteriorFromLoglik(space.prior, ll);
  }

  function predictContinue(space, post, k) {
    var s = 0.0;
    for (var i = 0; i < post.length; i++) s += post[i] * pContinue(space.chains[i], k);
    return s;
  }

  function classTotals(space, post) {
    var out = { switchy: 0.0, steady: 0.0, sticky: 0.0 };
    for (var i = 0; i < post.length; i++) out[CLASS_NAMES[space.chains[i].kind]] += post[i];
    return out;
  }

  function predictAfter(space, experience, shown) {
    var postExp = posterior(space, experience);
    var ll = space.chains.map(function (c) {
      return logLikelihood(c, experience) + logLikelihood(c, shown);
    });
    var postAll = posteriorFromLoglik(space.prior, ll);
    var k = endStreak(shown);
    return {
      prior: space.prior.slice(),
      after_experience: postExp,
      after_experience_classes: classTotals(space, postExp),
      after_shown: postAll,
      after_shown_classes: classTotals(space, postAll),
      streak: k,
      p_continue: predictContinue(space, postAll, k),
    };
  }

  /* ---- what the learner is shown after its experience ---- */
  function shownSequences(mode, length) {
    length = length === undefined ? DEFAULT_SHOWN_LENGTH : length;
    var groups = [];
    var s, t;
    if (mode === "streak") {
      for (s = 1; s <= length; s++) {
        var seq = [0];
        for (t = 0; t < s; t++) seq.push(1);
        groups.push([seq]);
      }
      return groups;
    }
    if (mode !== "iid8") throw new Error("unknown shown mode " + mode);
    for (s = 0; s < length; s++) groups.push([]);
    var total = Math.pow(2, length);
    for (var v = 0; v < total; v++) {
      var q = [];
      for (t = 0; t < length; t++) q.push((v >> t) & 1);
      groups[endStreak(q) - 1].push(q);
    }
    return groups;
  }

  /* ---- average over simulated learners ---- */
  function runAgents(space, ns, kAgents, seed, shownMode, shownLength, pathLength) {
    shownLength = shownLength === undefined ? DEFAULT_SHOWN_LENGTH : shownLength;
    if (shownMode === undefined) shownMode = "iid8";
    var nsSorted = Array.from(new Set(ns)).sort(function (a, b) {
      return a - b;
    });
    var nmax = nsSorted.length ? nsSorted[nsSorted.length - 1] : 0;
    if (pathLength !== undefined && pathLength !== null && pathLength < nmax) {
      throw new Error("pathLength " + pathLength + " is shorter than the largest level " + nmax);
    }
    var extraDraws = pathLength === undefined || pathLength === null ? 0 : pathLength - nmax;
    var chains = space.chains;
    var nh = chains.length;
    var prior = space.prior;
    var maxLen = nmax + shownLength + 1;
    var h, k;

    // log P(continue) and log P(switch) tables per hypothesis and streak length
    var lc = [];
    var ls = [];
    for (h = 0; h < nh; h++) {
      var rc = new Float64Array(maxLen + 1);
      var rs = new Float64Array(maxLen + 1);
      for (k = 0; k <= maxLen; k++) {
        var pc = pContinue(chains[h], Math.max(k, 1));
        rc[k] = Math.log(pc);
        rs[k] = Math.log(1.0 - pc);
      }
      lc.push(rc);
      ls.push(rs);
    }

    // shown sequences: E[h] = exp(loglik of the shown sequence), PC[h] = P(continue) at its end
    var groups = null;
    if (shownMode !== null) {
      var raw = shownSequences(shownMode, shownLength);
      groups = raw.map(function (group, gi) {
        var s = gi + 1;
        var n = group.length;
        var E = new Float64Array(n * nh);
        var PC = new Float64Array(nh);
        for (var h2 = 0; h2 < nh; h2++) PC[h2] = pContinue(chains[h2], s);
        for (var q = 0; q < n; q++) {
          for (var h3 = 0; h3 < nh; h3++) E[q * nh + h3] = Math.exp(logLikelihood(chains[h3], group[q]));
        }
        return { n: n, E: E, PC: PC };
      });
    }

    var sumsPost = {};
    var sumsPc = {};
    var above = {};
    var below = {};
    nsSorted.forEach(function (n) {
      sumsPost[n] = new Float64Array(nh);
      sumsPc[n] = new Float64Array(shownLength);
      above[n] = new Float64Array(shownLength);
      below[n] = new Float64Array(shownLength);
    });

    var a = new Float64Array(nh);
    function accumulate(n, ll) {
      var m = -Infinity;
      var i;
      for (i = 0; i < nh; i++) if (ll[i] > m) m = ll[i];
      var z = 0.0;
      for (i = 0; i < nh; i++) {
        a[i] = prior[i] * Math.exp(ll[i] - m);
        z += a[i];
      }
      var sp = sumsPost[n];
      for (i = 0; i < nh; i++) sp[i] += a[i] / z;
      if (groups === null) return;
      for (var si = 0; si < groups.length; si++) {
        var g = groups[si];
        var E = g.E;
        var PC = g.PC;
        var acc = 0.0;
        for (var q = 0; q < g.n; q++) {
          var num = 0.0;
          var den = 0.0;
          var base = q * nh;
          for (var hh = 0; hh < nh; hh++) {
            var w = a[hh] * E[base + hh];
            num += w * PC[hh];
            den += w;
          }
          var p = num / den;
          acc += p;
          if (p > HIT_RATE + TIE_TOLERANCE) above[n][si] += 1;
          else if (p < HIT_RATE - TIE_TOLERANCE) below[n][si] += 1;
        }
        sumsPc[n][si] += acc;
      }
    }

    var rng = new Mulberry32(seed);
    var ll = new Float64Array(nh);
    for (var agent = 0; agent < kAgents; agent++) {
      for (h = 0; h < nh; h++) ll[h] = 0.0;
      var streak = 0;
      var prev = -1;
      var ni = 0;
      if (nsSorted.length && nsSorted[0] === 0) {
        accumulate(0, ll);
        ni = 1;
      }
      for (var t = 1; t <= nmax; t++) {
        var x = rng.flip();
        if (t === 1) {
          for (h = 0; h < nh; h++) ll[h] += Math.log(HIT_RATE);
          streak = 1;
        } else if (x === prev) {
          for (h = 0; h < nh; h++) ll[h] += lc[h][streak];
          streak += 1;
        } else {
          for (h = 0; h < nh; h++) ll[h] += ls[h][streak];
          streak = 1;
        }
        prev = x;
        if (ni < nsSorted.length && nsSorted[ni] === t) {
          accumulate(t, ll);
          ni += 1;
        }
      }
      for (var d = 0; d < extraDraws; d++) rng.flip(); // draw and discard: fixed path per learner
    }

    return nsSorted.map(function (n) {
      var classPost = { switchy: 0.0, steady: 0.0, sticky: 0.0 };
      for (var i = 0; i < nh; i++) classPost[CLASS_NAMES[chains[i].kind]] += sumsPost[n][i] / kAgents;
      var row = { n: n, class_post: classPost, pcont: [], share_above: [] };
      if (groups !== null) {
        for (var si = 0; si < shownLength; si++) {
          row.pcont.push(sumsPc[n][si] / (kAgents * groups[si].n));
          var ab = above[n][si];
          var be = below[n][si];
          row.share_above.push(ab + be > 0 ? ab / (ab + be) : null);
        }
      }
      return row;
    });
  }

  function crossingStreak(pcont) {
    for (var i = 0; i < pcont.length; i++) {
      if (pcont[i] > HIT_RATE + TIE_TOLERANCE) return i + 1;
    }
    return null;
  }

  return {
    HIT_RATE: HIT_RATE,
    DEFAULT_STEPS: DEFAULT_STEPS,
    DEFAULT_DEGREE: DEFAULT_DEGREE,
    DEFAULT_MAX_STEPS: DEFAULT_MAX_STEPS,
    DEFAULT_SHOWN_LENGTH: DEFAULT_SHOWN_LENGTH,
    SWITCHY: SWITCHY,
    STEADY: STEADY,
    STICKY: STICKY,
    Mulberry32: Mulberry32,
    steadySequence: steadySequence,
    chain: chain,
    shift: shift,
    pContinue: pContinue,
    logLikelihood: logLikelihood,
    endStreak: endStreak,
    buildSpace: buildSpace,
    posteriorFromLoglik: posteriorFromLoglik,
    posterior: posterior,
    predictContinue: predictContinue,
    classTotals: classTotals,
    predictAfter: predictAfter,
    shownSequences: shownSequences,
    runAgents: runAgents,
    crossingStreak: crossingStreak,
  };
});
