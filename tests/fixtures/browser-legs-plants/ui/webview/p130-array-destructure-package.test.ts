import { test } from "node:test";
const [a, b] = require("node:os");
test("p130", () => { void a; void b; });
