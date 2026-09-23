import { test } from "node:test";
const spec = "./decoy-helper";
let leg: any;
switch (process.env.PLANT_K ?? "") { default: const spec = "./real-viewer-leg"; leg = require(spec); }
test("p313", async (t) => { await leg.inBrowser(t, async () => {}, "firefox"); });
