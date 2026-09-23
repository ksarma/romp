import { test } from "node:test";
const spec = "./decoy-helper";
let pw: any;
switch (process.env.PLANT_K ?? "") { default: const spec = "playwright"; pw = require(spec); }
test("p312", async () => { const b = await pw.firefox.launch(); await b.close(); });
