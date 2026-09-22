import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p79", (t) => inBrowser.call(null, t, async () => {}, "webkit"));
