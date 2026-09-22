import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const { inBrowser } = leg;
test("p60", async (t) => { await inBrowser(t, async () => {}); });
