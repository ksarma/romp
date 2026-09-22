import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p77", (t) => inBrowser(t, async () => {}, "firefox"));
