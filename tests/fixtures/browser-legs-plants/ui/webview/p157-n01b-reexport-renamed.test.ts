import { test } from "node:test";
import { load } from "./rcjs-barrel-renamed";
test("p157", async () => { const b = await load("playwright").webkit.launch(); await b.close(); });
