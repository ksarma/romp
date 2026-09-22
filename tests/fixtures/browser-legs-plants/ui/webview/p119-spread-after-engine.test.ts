import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p119", (t) => { const extra = [1, 2] as const; return (inBrowser as any)(t, async () => {}, "firefox", ...extra); });
