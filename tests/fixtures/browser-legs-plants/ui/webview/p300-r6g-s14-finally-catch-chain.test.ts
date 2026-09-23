import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p300", async (t) => { await inBrowser(t, async () => {}).finally(() => {}).catch(() => {}); });
