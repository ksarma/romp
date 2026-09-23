import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p345", async (t) => { const ps = [inBrowser(t, async () => {})]; await Promise.allSettled(ps); });
