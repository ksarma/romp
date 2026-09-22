import { test } from "node:test";
test("p112", async () => { const b = await require("playwright")[process.env.ENGINE as string].launch(); await b.close(); });
