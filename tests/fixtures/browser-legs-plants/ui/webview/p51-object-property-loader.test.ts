import { test } from "node:test";
const o = { pw: require("playwright") };
test("p51", async () => { const b = await o.pw.chromium.launch(); await b.close(); });
