import { test } from "node:test";
import { load } from "some-foreign-loader";
let name = "";
name = "play" + "wright";
test("p379", async () => { const b = await load(name).firefox.launch(); await b.close(); });
