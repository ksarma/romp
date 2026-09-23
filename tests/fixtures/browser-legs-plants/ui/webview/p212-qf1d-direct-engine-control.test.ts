import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p212", (t) => inBrowser(t, async () => {}, "firefox" as any));
