import { test } from "node:test";
const pw = require("playwright");
function which(): string { return process.env.ENGINE as string; }
test("p64", async () => { const b = await (pw as any)[which()].launch(); await b.close(); });
