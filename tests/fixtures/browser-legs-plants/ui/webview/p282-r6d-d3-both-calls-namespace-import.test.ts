import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import * as B from "./leg-barrel";
test("d3 direct call and a call through the barrel imported whole", async (t) => { await inBrowser(t, async () => {}); await B.inBrowser(t, async () => {}, "webkit"); });
