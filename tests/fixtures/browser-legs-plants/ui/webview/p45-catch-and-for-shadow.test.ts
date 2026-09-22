import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p45", async (t) => {
  try { throw new Error("x"); } catch (inBrowser) { void inBrowser; }
  for (const inBrowser of [1, 2]) { void inBrowser; }
  await inBrowser(t, async () => {});
});
