import { test } from "node:test";
const { inBrowser } = require("ui/webview/real-viewer-" + process.env.PLANT_X + "leg");
test("p347", (t) => inBrowser(t, async () => {}));
