// Runs docs/model.js on the cases given as JSON on stdin and prints the results as JSON.
// Used by tests/test_crosscheck_js.py to compare the JavaScript port with the Python reference.
const path = require("path");
const M = require(path.join(__dirname, "..", "docs", "model.js"));

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
  const cases = JSON.parse(input);
  const out = cases.map((c) => {
    if (c.kind === "agents") {
      const space = M.buildSpace(c.space);
      const rows = M.runAgents(space, c.ns, c.k, c.seed, c.shown_mode, c.shown_length, c.path_length);
      return { rows, crossings: rows.map((r) => M.crossingStreak(r.pcont)) };
    }
    if (c.kind === "learner") {
      const space = M.buildSpace(c.space);
      return M.predictAfter(space, c.experience, c.shown);
    }
    if (c.kind === "sequence") {
      return M.steadySequence(c.seed, c.n);
    }
    if (c.kind === "loglik") {
      return c.chains.map((ch) => M.logLikelihood(M.chain(ch[0], ch[1], ch[2]), c.seq));
    }
    throw new Error("unknown case kind " + c.kind);
  });
  process.stdout.write(JSON.stringify(out));
});
