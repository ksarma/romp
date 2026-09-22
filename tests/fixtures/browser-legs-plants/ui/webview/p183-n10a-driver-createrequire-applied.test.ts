import { test } from "node:test";
const DRIVER = `const { createRequire } = require("node:module"); const pw = createRequire(process.argv[1] + "/package.json")("playwright"); pw.firefox.launch().then((b) => b.close());`;
test("p183", () => { void DRIVER; });
