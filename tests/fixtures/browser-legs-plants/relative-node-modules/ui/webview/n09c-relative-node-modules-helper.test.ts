import { test } from "node:test";
import { open } from "./relpw-helper";
test("n09c", async () => { const b = await open(); await b.close(); });
