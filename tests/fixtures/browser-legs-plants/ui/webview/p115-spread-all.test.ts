import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p115", (t) => { const run = [t, async () => {}, "firefox"] as const; return (inBrowser as any)(...run); });
