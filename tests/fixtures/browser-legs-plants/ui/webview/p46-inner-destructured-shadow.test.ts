import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p46", async (t) => { { const { inBrowser } = { inBrowser: async (_t: any, f: any) => f() }; await inBrowser(t, async () => {}); } });
