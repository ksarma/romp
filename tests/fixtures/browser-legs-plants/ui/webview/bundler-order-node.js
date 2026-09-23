// a plant's companion, not a test module: the .js beside bundler-order-node.ts, the file node resolves when the test runs for the
// specifier ../ui/webview/bundler-order-node, which a loader bound to the working directory's package.json passes, since npm test
// runs in vscode-extension/ and node tries .js and never .ts (p392); it launches Firefox itself
const { firefox } = require("playwright");
exports.go = async function () { const b = await firefox.launch(); await b.close(); };
