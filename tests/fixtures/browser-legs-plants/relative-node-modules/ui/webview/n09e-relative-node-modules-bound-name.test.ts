import { test } from "node:test";
function load(spec: string): any { return spec; }
const spec = "../../vscode-extension/node_modules/playwright";
test("n09e", async () => { const b = await load(spec).webkit.launch(); await b.close(); });
