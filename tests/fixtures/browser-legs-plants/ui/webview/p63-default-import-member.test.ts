import { test } from "node:test";
import leg from "./real-viewer-leg";
test("p63", async (t) => { await leg.inBrowser(t, async () => {}); });
