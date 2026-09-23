import { test } from "node:test";
import pw from "playwright";
const k = process.env.K as string;
test("p201", async () => { const b = await pw[k](); await b.close(); });
