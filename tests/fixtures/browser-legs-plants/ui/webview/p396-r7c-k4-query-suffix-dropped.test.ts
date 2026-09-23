import { test } from "node:test";
const h = require("./bundler-suffix-query?raw");
test("p396", async () => { await h.go(); });
