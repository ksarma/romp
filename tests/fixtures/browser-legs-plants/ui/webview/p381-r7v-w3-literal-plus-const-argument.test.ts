import { test } from "node:test";
import { load } from "some-foreign-loader";
const tail = "wright";
test("p381", async () => { const b = await load("play" + tail).firefox.launch(); await b.close(); });
