import { test } from "node:test";
import path from "node:path";
const leg = require(path.resolve(process.cwd(), "..", "ui", "webview", "real-viewer-leg.cjs"));
test("p349", (t) => leg.inBrowser(t, async () => {}));
