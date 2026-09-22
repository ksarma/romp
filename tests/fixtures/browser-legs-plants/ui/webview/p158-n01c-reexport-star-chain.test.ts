import { test } from "node:test";
import { requireCjs } from "./rcjs-barrel-star";
test("p158", async () => { const b = await requireCjs("playwright").firefox.launch(); await b.close(); });
