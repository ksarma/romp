import { test } from "node:test";
const DRIVER = `const pw = require("${process.env.PKG}"); pw.chromium.launch().then((b) => b.close());`;
test("p68", () => { void DRIVER; });
