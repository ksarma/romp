import { test } from "node:test";
function load(): any { return require("playwright"); }
test("p274", async () => { const b = await require("playwright").firefox.launch(); await b.close(); const w = await load().webkit.launch(); await w.close(); });
