import { test } from "node:test";
import leg from "./real-viewer-leg";
const l = leg ?? null;
test("p145", (t) => l.inBrowser(t, async () => {}));
