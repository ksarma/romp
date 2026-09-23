// a plant's companion, not a test module: the spelled path ./bundler-order-dotjs.js with the suffix .ts added, which the bundler tries
// before it rewrites the spelling to bundler-order-dotjs.ts, so it is the file the bundler loads (p391); it launches Firefox itself
const { firefox } = require("playwright");
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
