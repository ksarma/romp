import { test } from "node:test";
const h = require("./bundler-jsx-helper.jsx");
test("p374", async () => { await h.go(); });
