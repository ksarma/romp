import { test } from "node:test";
import path from "node:path";
const { inBrowser } = require(path.resolve(process.cwd(), "..", "ui", "webview", "real-viewer-leg-stub"));
test("p323", (t) => inBrowser(t, async () => {}));
