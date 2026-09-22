import { test } from "node:test";
const p = import("./real-viewer-leg");
test("p82", (t) => p.then(({ inBrowser }) => inBrowser(t, async () => {})));
