import { test } from "node:test";
import path from "node:path";
const { inBrowser } = require(path.resolve(process.cwd(), "real-viewer-leg-amb"));
test("p329", (t) => inBrowser(t, async () => {}));
