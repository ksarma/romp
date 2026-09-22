import { test } from "node:test";
const pw = require("../../vscode-extension/node_modules/playwright");
test("n09b", async () => { const b = await pw.webkit.launch(); await b.close(); });
