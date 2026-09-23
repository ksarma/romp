import { test } from "node:test";
let pw: any = null;
try { pw = require("playwright"); } catch { pw = null; }
test("p198", async () => { if (!pw || (pw !== null && typeof pw !== "object")) return; const b = await pw.firefox.launch(); await b.close(); });
