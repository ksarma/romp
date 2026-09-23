import { test } from "node:test";
const bag = { pw: require("playwright") };
test("p269", async () => { const b = await require("playwright").firefox.launch(); await b.close(); const w = await bag.pw.webkit.launch(); await w.close(); });
