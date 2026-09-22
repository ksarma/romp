import { test } from "node:test";
let pw: any = 1;
test("p181", async () => { pw &&= await import("playwright"); const b = await pw.firefox.launch(); await b.close(); });
