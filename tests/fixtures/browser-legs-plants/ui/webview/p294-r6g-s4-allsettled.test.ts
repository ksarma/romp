import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p294", async (t) => { await Promise.allSettled([inBrowser(t, async () => {})]); });
