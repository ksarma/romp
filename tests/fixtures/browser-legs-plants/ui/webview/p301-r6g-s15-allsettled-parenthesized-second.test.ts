import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p301", async (t) => { await Promise.allSettled([Promise.resolve(), (inBrowser(t, async () => {}))]); });
