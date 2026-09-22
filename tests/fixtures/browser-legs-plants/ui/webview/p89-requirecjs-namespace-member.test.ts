import { test } from "node:test";
import * as leg from "./real-viewer-leg";
test("p89", async () => { const b = await leg.requireCjs("playwright").firefox.launch(); await b.close(); });
