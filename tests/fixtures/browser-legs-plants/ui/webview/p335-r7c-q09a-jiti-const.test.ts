import { test } from "node:test";
import jiti from "jiti";
const pkg = "playwright";
const pw = jiti(__filename)(pkg);
test("p335", async () => { const b = await pw.firefox.launch(); await b.close(); });
