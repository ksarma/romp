import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p385", async (t) => { await Promise["allSettled"]([inBrowser(t, async () => {})]); });
