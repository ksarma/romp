import { test } from "node:test";
const { constants: { signals } } = require("node:os");
test("p131", () => { void signals; });
