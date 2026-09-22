import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const r = leg.requireCjs;
test("p96", async () => { const b = await r("playwright").firefox.launch(); await b.close(); });
