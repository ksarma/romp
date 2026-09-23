import { test } from "node:test";
import { load } from "some-foreign-loader";
const head = "play";
const name = head + "wright";
test("p382", async () => { const b = await load(name).firefox.launch(); await b.close(); });
