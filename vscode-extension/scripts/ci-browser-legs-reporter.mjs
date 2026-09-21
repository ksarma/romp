// The browser-legs step's reporter for node --test. scripts/ci-browser-legs.sh passes it beside the spec reporter
// (--test-reporter=./scripts/ci-browser-legs-reporter.mjs --test-reporter-destination=<file>) and reads its stream after the
// run, so every result is attributed to its bundle by node's own record of the file: node's TAP record, in a run over many
// files, reports every test at the top level with no file name (a pass carries no location; only a failure does), so a TAP
// reader cannot say which rostered leg a pass belongs to. One line per test:pass or test:fail event, eight tab-separated fields:
//   1 the bundle's absolute path (node's data.file, resolved from the process's physical working directory);
//   2 pass or fail;
//   3 test or suite (a describe() reports as a suite; a suite's own pass is never a test of the leg);
//   4 the directive: skip, todo, or - (a skipped test reports as a pass with a skip; a todo test reports as a pass or a fail with
//     a todo, and node counts neither as a failure, so a real assertion failure inside a todo leaves node's exit at 0);
//   5 file-level or test: node enqueues one test per FILE (nesting 0, line 1, column 1, named by the path argument as node
//     received it) and reports it as a pass only when the file registered no test of its own, and as a fail when the file timed
//     out under --test-timeout or threw at load; so a file-level pass is a leg that ran nothing, and a file-level fail names the
//     file that failed as a whole;
//   6 the test's name; 7 the skip or todo reason of a pass, or the failure's message (the cause's, when node wrapped it);
//   8 the failure type (testCodeFailure, testTimeoutFailure, ...) or -.
// A backslash, tab, newline or carriage return inside a name or a message is written \\ \t \n \r, so a line is one result.
// Plain ESM with no dependency, so the tree test (tools/ci-browser-legs.test.mjs) executes it over synthetic bundles with the
// node CI's Shell job has, without npm ci.
export default async function* reporter(source) {
  const esc = (s) => String(s === undefined || s === null ? "" : s).replace(/\\/g, "\\\\").replace(/\t/g, "\\t").replace(/\n/g, "\\n").replace(/\r/g, "\\r");
  const fileLevel = new Set();
  for await (const ev of source) {
    const d = ev.data;
    if (!d) continue;
    if (ev.type === "test:enqueue" && d.nesting === 0 && d.line === 1 && d.column === 1 && typeof d.file === "string" && typeof d.name === "string" && d.file.endsWith(d.name.replace(/^\.\//, ""))) fileLevel.add(d.file + "\0" + d.name);
    if (ev.type !== "test:pass" && ev.type !== "test:fail") continue;
    const pass = ev.type === "test:pass";
    const err = d.details && d.details.error;
    const cause = err && err.cause && err.cause.message !== undefined ? err.cause : err;
    const directive = d.skip !== undefined ? "skip" : d.todo !== undefined ? "todo" : "-";
    const reason = pass ? (typeof d.skip === "string" ? d.skip : typeof d.todo === "string" ? d.todo : "") : (cause && cause.message) || "";
    const synthesized = d.nesting === 0 && fileLevel.has(d.file + "\0" + d.name) ? "file-level" : "test";
    yield [d.file || "-", pass ? "pass" : "fail", (d.details && d.details.type) || "test", directive, synthesized, esc(d.name), esc(reason), (err && err.failureType) || "-"].join("\t") + "\n";
  }
}
