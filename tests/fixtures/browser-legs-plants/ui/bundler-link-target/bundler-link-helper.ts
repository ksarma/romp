// a plant's companion, not a test module: the file ../bundler-link-helper names beside the link's real path, which the bundler
// loads through ui/webview/bundler-link-dir (p398); it launches Firefox itself
const { firefox } = require("playwright");
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
