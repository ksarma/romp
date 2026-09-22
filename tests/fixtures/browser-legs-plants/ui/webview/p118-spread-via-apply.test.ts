import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p118", (t) => { const rest = [async () => {}, "webkit"] as const; return (inBrowser as any).apply(null, [t, ...rest]); });
