import { test } from "node:test";
const DRIVER = `import { createRequire } from "node:module"; const req = createRequire(import.meta.url); const pw = req("playwright"); pw.firefox.launch().then((b) => b.close());`;
test("p185", () => { void DRIVER; });
