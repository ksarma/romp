import { test } from "node:test";
import { load } from "some-foreign-loader";
const name = "play" + "wright";
test("p377", async () => { const b = await load(name).firefox.launch(); await b.close(); });
