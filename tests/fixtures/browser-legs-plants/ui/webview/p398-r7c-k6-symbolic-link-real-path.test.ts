import { test } from "node:test";
const h = require("./bundler-link-dir");
test("p398", async () => { await h.go(); });
