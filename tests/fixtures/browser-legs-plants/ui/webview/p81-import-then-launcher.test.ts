import { test } from "node:test";
test("p81", (t) => import("./real-viewer-leg").then((m) => m.inBrowser(t, async () => {})));
