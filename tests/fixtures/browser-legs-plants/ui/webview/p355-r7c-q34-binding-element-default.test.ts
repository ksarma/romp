import { test } from "node:test";
import { load } from "some-foreign-loader";
const { spec = "playwright" }: { spec?: string } = {};
test("p355", async () => { const b = await load(spec).firefox.launch(); await b.close(); });
