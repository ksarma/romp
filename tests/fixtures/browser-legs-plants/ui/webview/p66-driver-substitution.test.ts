import { test } from "node:test";
const PKG = "playwright";
const DRIVER = `const pw = require("${PKG}"); pw.chromium.launch().then((b) => b.close());`;
test("p66", () => { void DRIVER; });
