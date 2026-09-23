// a plant's companion, not a test module: the index.ts the package.json beside it names as ./index.js, the file the bundler loads
// for a specifier spelled ./bundler-pkg-main-js (p394); it launches Firefox itself
const { firefox } = require("playwright");
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
