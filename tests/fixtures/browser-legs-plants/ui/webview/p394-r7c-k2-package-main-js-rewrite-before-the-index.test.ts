import { test } from "node:test";
const h = require("./bundler-pkg-main-js");
test("p394", async () => { await h.go(); });
