import { test } from "node:test";
import { load } from "some-foreign-loader";
const cfg = { pkg: "playwright" };
test("p341", async () => { const b = await load(cfg.pkg).firefox.launch(); await b.close(); });
