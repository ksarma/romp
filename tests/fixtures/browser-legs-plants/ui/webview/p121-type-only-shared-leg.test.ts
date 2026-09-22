import { test } from "node:test";
import type { Browser } from "playwright";
import { inBrowser } from "./real-viewer-leg";
test("p121", (t) => inBrowser(t, async (b: Browser) => { void b; }));
