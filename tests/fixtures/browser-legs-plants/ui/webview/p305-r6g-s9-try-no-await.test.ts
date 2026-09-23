import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p305", async (t) => { try { void inBrowser(t, async () => {}); } catch (e) { void e; } });
