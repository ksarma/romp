import { test } from "node:test";
import { requireCjs } from "./real-viewer-leg";
let spec = "./decoy-helper";
spec = "playwright";
const pw = requireCjs(spec);
test("p242", async () => { const b = await pw.firefox.launch(); await b.close(); });
