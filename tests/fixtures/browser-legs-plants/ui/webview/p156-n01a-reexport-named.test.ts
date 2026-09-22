import { test } from "node:test";
import { requireCjs } from "./rcjs-barrel";
test("p156", async () => { const b = await requireCjs("playwright").firefox.launch(); await b.close(); });
