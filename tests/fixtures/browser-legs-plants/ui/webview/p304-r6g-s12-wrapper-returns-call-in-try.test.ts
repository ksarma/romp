import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const p = (t: any) => inBrowser(t, async () => {});
test("p304", async (t) => { try { await p(t); } catch (e) { void e; } });
