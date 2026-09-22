import { test } from "node:test";
const DRIVER = `const pw = require("playwright/test"); pw.webkit.launch().then((b) => b.close());`;
test("p184", () => { void DRIVER; });
