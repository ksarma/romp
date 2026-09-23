import { test } from "node:test";
const DRIVER = `function load(s) { return require(s); } const pw = load("playwright"); pw.firefox.launch().then((b) => b.close());`;
test("p199", () => { void DRIVER; });
