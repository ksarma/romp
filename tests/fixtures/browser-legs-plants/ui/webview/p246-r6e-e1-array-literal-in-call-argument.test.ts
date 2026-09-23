import { test } from "node:test";
function load(a: string[]): any { return a[0]; }
test("e1 array literal in a call's argument", async () => { const b = await load(["playwright"]).firefox.launch(); await b.close(); });
