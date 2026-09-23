import { test } from "node:test";
import { load } from "some-foreign-loader";
const head = "play";
test("p383", async () => { const b = await load(`${head}wright`).firefox.launch(); await b.close(); });
