// a plant's companion, not a test module: the .js beside bundler-order-node.ts, the file node resolves for the specifier
// ./bundler-order-node when the test runs, since node tries .js and never .ts (p392); it launches Firefox itself
const { firefox } = require("playwright");
exports.go = async function () { const b = await firefox.launch(); await b.close(); };
