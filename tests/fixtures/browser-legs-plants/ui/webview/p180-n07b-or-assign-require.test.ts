import { test } from "node:test";
let pw: any = null;
test("p180", async () => { pw ||= require("playwright"); const b = await pw.webkit.launch(); await b.close(); });
