import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p297", async (t) => { await inBrowser(t, async () => {}).finally(() => {}); });
