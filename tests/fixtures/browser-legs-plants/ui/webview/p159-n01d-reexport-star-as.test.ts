import { test } from "node:test";
import { ns } from "./rcjs-barrel-star-as";
test("p159", async () => { const b = await ns.requireCjs("playwright").webkit.launch(); await b.close(); });
