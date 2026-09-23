import { test } from "node:test";
import { load } from "some-foreign-loader";
const part = "wright";
const name = `play${part}`;
test("p378", async () => { const b = await load(name).firefox.launch(); await b.close(); });
