import { test } from "node:test";
let pw: any;
pw ??= require("playwright");
test("p179", async () => { const b = await pw.firefox.launch(); await b.close(); });
