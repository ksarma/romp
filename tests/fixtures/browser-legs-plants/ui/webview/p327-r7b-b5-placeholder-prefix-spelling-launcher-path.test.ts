import { test } from "node:test";
const { inBrowser } = require(process.env.LEG_ROOT + "/ui/webview/real-viewer-leg");
test("p327", (t) => inBrowser(t, async () => {}));
