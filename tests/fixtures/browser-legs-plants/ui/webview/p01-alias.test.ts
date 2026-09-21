import { test } from "node:test";
import { inBrowser as runInBrowser } from "./real-viewer-leg";
test("p1", (t) => runInBrowser(t, async () => {}));
