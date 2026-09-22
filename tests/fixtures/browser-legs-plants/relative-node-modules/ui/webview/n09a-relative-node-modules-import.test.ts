import { test } from "node:test";
import { firefox } from "../../vscode-extension/node_modules/playwright";
test("n09a", async () => { const b = await firefox.launch(); await b.close(); });
