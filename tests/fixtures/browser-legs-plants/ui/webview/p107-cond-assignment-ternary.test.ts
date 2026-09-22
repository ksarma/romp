import { test } from "node:test";
let pw: any;
pw = process.env.FLAG ? require("playwright") : null;
test("p107", async () => { const b = await pw.firefox.launch(); await b.close(); });
