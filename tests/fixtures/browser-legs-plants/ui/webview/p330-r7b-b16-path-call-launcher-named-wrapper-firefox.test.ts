import { test } from "node:test";
import path from "node:path";
const { inBrowser } = require(path.resolve(process.cwd(), "..", "ui", "webview", "real-viewer-leg-wrap"));
test("p330", (t) => inBrowser(t, async () => {}));
