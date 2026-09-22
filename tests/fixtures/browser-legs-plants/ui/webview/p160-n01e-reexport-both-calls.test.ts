import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { requireCjs } from "./rcjs-barrel";
test("p160", async (t) => { await inBrowser(t, async () => { const b = await requireCjs("playwright").firefox.launch(); await b.close(); }); });
