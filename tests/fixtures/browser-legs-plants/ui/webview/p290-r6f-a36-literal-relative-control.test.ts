import { test } from "node:test";
const m = require("./playwright");
test("a36 the literal control", async (t) => { await m.run(t); });
