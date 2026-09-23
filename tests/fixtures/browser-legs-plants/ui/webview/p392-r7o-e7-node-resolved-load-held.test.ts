import { test } from "node:test";
import { createRequire } from "node:module";
const load = createRequire(__filename);
const h = load("./bundler-order-node");
test("p392", async () => { await h.go(); });
