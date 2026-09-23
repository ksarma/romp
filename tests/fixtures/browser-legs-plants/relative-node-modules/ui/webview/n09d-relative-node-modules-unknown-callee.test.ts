import { test } from "node:test";
function load(spec: string): any { return spec; }
test("n09d", async () => { const b = await load("../../vscode-extension/node_modules/playwright").webkit.launch(); await b.close(); });
