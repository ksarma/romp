import { test } from "node:test";
const h = require("./bundler-order-jsx");
test("p388", async () => { await h.go(); });
