import { test } from "node:test";
import { load } from "some-foreign-loader";
class Cfg { spec = "playwright"; }
test("p359", async () => { const b = await load(new Cfg().spec).firefox.launch(); await b.close(); });
