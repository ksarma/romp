import { test } from "node:test";
const m = require("./play" + "wright");
test("a34 a relative module's name from two literals, a decoy at the slash-joined path", async (t) => { await m.run(t); });
