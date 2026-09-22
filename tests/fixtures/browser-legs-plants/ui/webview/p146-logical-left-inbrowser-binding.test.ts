import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p146", (t) => (inBrowser ?? null)(t, async () => {}));
