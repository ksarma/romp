import { test } from "node:test";
let spec = "./decoy-helper";
spec = "../../vscode-extension/node_modules/playwright";
const pw = require(spec);
test("p244", async () => { const b = await pw.firefox.launch(); await b.close(); });
