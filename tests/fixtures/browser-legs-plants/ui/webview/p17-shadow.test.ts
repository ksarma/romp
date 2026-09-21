import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p17", async (t) => { const inBrowser = async (x: any, f: any) => { void x; await f(); }; await inBrowser(t, async () => {}); });
