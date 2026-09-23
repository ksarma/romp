// a plant's companion, not a test module: the .tsx beside bundler-order-twin.ts, the file the bundler loads for a specifier spelled
// ./bundler-order-twin, since the test build's suffix list tries .tsx before .ts (p386); it carries JSX and launches Firefox itself
const { firefox } = require("playwright");
export const view = <div />;
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
