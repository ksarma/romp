import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const o: { x?: (t: any, f: () => Promise<void>) => Promise<void> } = {};
const { x = inBrowser } = o;
test("p30", (t) => x(t, async () => {}));
