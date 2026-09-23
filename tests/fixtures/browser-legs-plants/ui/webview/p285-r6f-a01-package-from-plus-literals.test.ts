import { test } from "node:test";
const pw = require("play" + "wright");
test("a01 the package's name from two literals", async () => { const b = await pw.webkit.launch(); await b.close(); });
