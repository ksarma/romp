import { test } from "node:test";
const DRIVER = 'const pw = require("' + "playwright" + '"); pw.chromium.launch().then((b) => b.close());';
test("p67", () => { void DRIVER; });
