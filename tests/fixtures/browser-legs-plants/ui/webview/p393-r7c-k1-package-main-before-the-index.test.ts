import { test } from "node:test";
const h = require("./bundler-pkg-main");
test("p393", async () => { await h.go(); });
