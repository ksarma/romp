// a plant's companion, not a test module: the directory's index.tsx beside its index.ts, the file the bundler loads for a specifier
// spelled ./bundler-order-dir, since it tries the index with the test build's suffixes in order, .tsx first (p390); it carries JSX
// and launches Firefox itself
const { firefox } = require("playwright");
export const view = <div />;
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
