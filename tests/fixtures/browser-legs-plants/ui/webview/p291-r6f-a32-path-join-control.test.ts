import { test } from "node:test";
import path from "node:path";
const m = require(path.join("./play", "wright"));
test("a32 the path-call control", () => { void m.nothing; });
