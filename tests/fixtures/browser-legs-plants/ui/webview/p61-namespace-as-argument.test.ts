import { test } from "node:test";
import * as leg from "./real-viewer-leg";
function go(m: any, t: any) { return m.inBrowser(t, async () => {}); }
test("p61", async (t) => { await go(leg, t); });
