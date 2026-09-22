import { test } from "node:test";
function L() { return require("./real-viewer-leg"); }
test("p52", async (t) => { await L().inBrowser(t, async () => {}); });
