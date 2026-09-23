// a plant's companion, not a test module: the file the bundler loads for a specifier spelled ./bundler-suffix-hash#frag, after it
// drops the #frag suffix (p397); it launches Firefox itself
const { firefox } = require("playwright");
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
