import { test } from "node:test";
const tail = "wright";
const m = require(`./play${tail}`);
test("a35 a relative module's name from a template, a decoy at the slash-joined path", async (t) => { await m.run(t); });
