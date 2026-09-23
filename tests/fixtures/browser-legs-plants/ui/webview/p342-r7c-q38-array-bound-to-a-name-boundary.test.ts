import { test } from "node:test";
import { load } from "some-foreign-loader";
const specs = ["playwright"];
test("p342", async () => { const b = await load(specs[0]).firefox.launch(); await b.close(); });
