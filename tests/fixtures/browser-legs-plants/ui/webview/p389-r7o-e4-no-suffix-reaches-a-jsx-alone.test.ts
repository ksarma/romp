import { test } from "node:test";
const h = require("./bundler-order-jsx-alone");
test("p389", async () => { await h.go(); });
