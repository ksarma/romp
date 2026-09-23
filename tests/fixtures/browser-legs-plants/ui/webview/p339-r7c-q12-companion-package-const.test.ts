import { test } from "node:test";
import { load } from "./plain-loader-helper";
const PKG = "playwright";
const pw = load(PKG);
test("p339", async () => { const b = await pw.firefox.launch(); await b.close(); });
