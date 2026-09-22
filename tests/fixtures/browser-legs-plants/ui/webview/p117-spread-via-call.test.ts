import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p117", (t) => { const rest = [async () => {}, "firefox"] as const; return (inBrowser as any).call(null, t, ...rest); });
