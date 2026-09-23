// the launcher's .js twin (a plant's companion, not a test module), in the plants root no-cjs-twin: a real-viewer-leg.js beside the
// stub launcher, the file the bundler loads for a specifier spelled ./real-viewer-leg.js before any rewrite to the .ts, and it
// launches Firefox itself (p376)
const { firefox } = require("playwright");
exports.inBrowser = async function (t, body) { void t; const b = await firefox.launch(); try { await body(b); } finally { await b.close(); } };
