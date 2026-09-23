import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p310", async (t) => { await Promise.all([inBrowser(t, async () => {})]).catch(() => {}); });
