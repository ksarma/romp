import { test } from "node:test";
const h = require("./bundler-order-twin");
test("p386", async () => { await h.go(); });
