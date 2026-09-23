import { test } from "node:test";
const h = require("./bundler-dts-only.js");
test("p375", async () => { await h.go(); });
