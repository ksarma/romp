// the launcher's .tsx twin (a plant's companion, not a test module), in a plants root of its own, since a .tsx beside the main tree's
// launcher would move every plant there that loads the launcher with no suffix: the file the bundler loads for a specifier spelled
// ./real-viewer-leg, since the test build's suffix list tries .tsx before .ts, and it launches Firefox itself (p387)
const { firefox } = require("playwright");
export const view = <div />;
export async function inBrowser(t: unknown, body: (b: unknown) => Promise<void>): Promise<void> { void t; const b = await firefox.launch(); try { await body(b); } finally { await b.close(); } }
