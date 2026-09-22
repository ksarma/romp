import { test } from "node:test";
import { requireCjs } from "./rcjs-lookalike";
test("p190", async () => { const b = await requireCjs("playwright").firefox.launch(); await b.close(); });
