import { test } from "node:test";
import { Loader } from "some-foreign-loader";
test("p362", async () => { const b = await new Loader({ spec: "playwright" }).module.firefox.launch(); await b.close(); });
