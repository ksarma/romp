import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p80", (t) => inBrowser(t, async () => {}, "chrome"));
