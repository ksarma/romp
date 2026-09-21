import { test } from "node:test";
import { firefox } from "playwright";
test("p9a", async () => { const b = await firefox.launch(); await b.close(); });
