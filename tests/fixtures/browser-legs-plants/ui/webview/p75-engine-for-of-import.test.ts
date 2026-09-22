import { test } from "node:test";
import { inBrowser, ENGINES } from "./real-viewer-leg";
for (const engine of ENGINES) test("p75 " + engine, (t) => inBrowser(t, async () => {}, engine));
