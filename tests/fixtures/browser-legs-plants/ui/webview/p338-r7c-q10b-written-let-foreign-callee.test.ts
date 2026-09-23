import { test } from "node:test";
import { load } from "some-foreign-loader";
let name = "./decoy-helper";
name = "playwright";
test("p338", async () => { const b = await load(name).firefox.launch(); await b.close(); });
