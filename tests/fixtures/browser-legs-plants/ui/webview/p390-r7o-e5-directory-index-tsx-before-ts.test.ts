import { test } from "node:test";
const h = require("./bundler-order-dir");
test("p390", async () => { await h.go(); });
