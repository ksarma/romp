import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const api = { open: inBrowser };
test("p13", (t) => api.open(t, async () => {}));
