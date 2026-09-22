import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p78", (t) => inBrowser(t, async () => {}, process.env.ENGINE as any));
