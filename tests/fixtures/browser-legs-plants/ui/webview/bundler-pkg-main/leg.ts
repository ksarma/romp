// a plant's companion, not a test module: the file the package.json beside it names as its main, which the bundler loads for a
// specifier spelled ./bundler-pkg-main before the directory's index (p393), and node for ../ui/webview/bundler-pkg-main loaded
// through a loader anchored at vscode-extension/, the working directory npm test runs in (p399); it launches Firefox itself
const { firefox } = require("playwright");
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
