import { test } from "node:test";
class Loader { constructor(private s: string) {} get(): any { return this.s; } }
test("e2 new expression's argument", async () => { const b = await new Loader("playwright").get().firefox.launch(); await b.close(); });
