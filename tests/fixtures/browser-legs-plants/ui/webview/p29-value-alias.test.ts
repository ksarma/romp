import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const f = inBrowser;
test("p29", (t) => f(t, async () => {}));
