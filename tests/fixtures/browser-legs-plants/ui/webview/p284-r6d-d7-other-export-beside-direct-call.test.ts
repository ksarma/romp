import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { helper } from "./leg-barrel-plus";
test("d7 the barrel imported for another export beside a direct call", async (t) => { helper(); await inBrowser(t, async () => {}); });
