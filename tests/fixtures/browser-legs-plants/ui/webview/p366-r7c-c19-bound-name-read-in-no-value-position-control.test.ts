import { test } from "node:test";
let name = "playwright";
name = "./decoy-helper";
const o = { name: 1 };
const { name: renamed } = o;
type T = typeof name;
name: { if (o.name && renamed) break name; }
test("p366", () => { const t: T = ""; void t; });
