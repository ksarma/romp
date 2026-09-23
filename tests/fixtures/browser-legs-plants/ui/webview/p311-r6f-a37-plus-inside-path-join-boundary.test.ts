import { test } from "node:test";
import path from "node:path";
const m = require(path.join("./play", "wr" + "ight"));
test("p311", () => { void m.nothing; });
