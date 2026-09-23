// a plant's companion, not a test module: the file the bundler loads for a specifier spelled ./bundler-suffix-query?raw, after it
// drops the ?raw suffix (p396); it launches Firefox itself
const { firefox } = require("playwright");
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
