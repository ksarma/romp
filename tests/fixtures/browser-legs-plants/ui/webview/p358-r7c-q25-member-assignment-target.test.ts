import { test } from "node:test";
import { load } from "some-foreign-loader";
const cfg: any = {};
cfg.pkg = "playwright";
test("p358", async () => { const b = await load(cfg.pkg).firefox.launch(); await b.close(); });
