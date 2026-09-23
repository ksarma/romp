// the launcher's .cts twin (a plant's companion, not a test module), in a plants root of its own whose launcher has no .cjs beside
// it: the file the bundler loads for a specifier spelled ./real-viewer-leg.cjs when no .cjs stands there, and it launches Firefox
// itself (p370)
const { firefox } = require("playwright");
exports.inBrowser = async function (t: unknown, body: (b: unknown) => Promise<void>): Promise<void> { void t; const b = await firefox.launch(); try { await body(b); } finally { await b.close(); } };
