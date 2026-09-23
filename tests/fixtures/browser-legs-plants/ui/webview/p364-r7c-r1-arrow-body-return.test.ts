import { test } from "node:test";
import { load } from "some-foreign-loader";
const pkg = (): string => "playwright";
test("p364", async () => { const b = await load(pkg()).firefox.launch(); await b.close(); });
