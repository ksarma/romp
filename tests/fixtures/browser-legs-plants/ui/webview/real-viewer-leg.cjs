// the launcher's CommonJS twin (a plant's companion, not a test module): a real-viewer-leg.cjs beside the stub launcher, which the
// bundler loads for a specifier spelled with .cjs, and which launches Firefox itself (p348, p349)
const { firefox } = require("playwright");
exports.inBrowser = async function (t, body) { void t; const b = await firefox.launch(); try { await body(b); } finally { await b.close(); } };
