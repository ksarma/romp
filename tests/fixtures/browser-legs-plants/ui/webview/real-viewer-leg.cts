// a .cts beside the launcher's .cjs twin (a plant's companion, not a test module): a specifier spelled ./real-viewer-leg.cjs loads
// the .cjs that stands there and never this rewrite of it (the bundler's order, the spelled path first), so p348 and p349 read the
// .cjs; it launches Firefox itself
const { firefox } = require("playwright");
exports.inBrowser = async function (t: unknown, body: (b: unknown) => Promise<void>): Promise<void> { void t; const b = await firefox.launch(); try { await body(b); } finally { await b.close(); } };
