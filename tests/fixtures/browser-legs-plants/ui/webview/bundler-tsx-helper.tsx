// a plant's companion, not a test module: a .tsx with no .ts beside it, which the bundler loads for a specifier spelled
// ./bundler-tsx-helper.js (p372); it carries JSX, so it parses as TSX alone, and launches Firefox itself
const { firefox } = require("playwright");
export const view = <div />;
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
