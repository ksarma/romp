// a module named like the launcher that wraps it with an engine (a plant's companion, not a test module): its inBrowser passes Firefox (p330)
const { inBrowser: ib } = require("./real-viewer-leg");
export const inBrowser = (t: any, body: (b: any) => Promise<void>) => ib(t, body, "firefox");
