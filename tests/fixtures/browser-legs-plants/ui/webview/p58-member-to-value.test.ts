import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const run = leg.inBrowser;
test("p58", async (t) => { await run(t, async () => {}); });
