import { test } from "node:test";
import * as real from "playwright";
const pw = process.env.FLAG ? real : null;
test("p106", async () => { const b = await pw.firefox.launch(); await b.close(); });
