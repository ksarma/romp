import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
function pick(name: string): string { return name; }
test("p191", async (t) => { await inBrowser(t, async () => { void pick("playwright"); }); });
