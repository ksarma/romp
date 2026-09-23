import { test } from "node:test";
const h = require("./bundler-order-dotjs.js");
test("p391", async () => { await h.go(); });
