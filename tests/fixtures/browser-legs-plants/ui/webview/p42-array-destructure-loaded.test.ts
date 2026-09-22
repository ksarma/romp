import { test } from "node:test";
const [x] = require("playwright");
test("p42", async () => { const b = await x.launch(); await b.close(); });
