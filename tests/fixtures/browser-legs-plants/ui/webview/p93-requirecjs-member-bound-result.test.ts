import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const pw = leg.requireCjs("playwright");
test("p93", async () => { const b = await pw.firefox.launch(); await b.close(); });
