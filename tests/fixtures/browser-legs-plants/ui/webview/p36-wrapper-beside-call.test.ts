import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { withPage } from "./leg-wrap";
test("p36a", (t) => inBrowser(t, async () => {}));
test("p36b", (t) => withPage(t, async () => {}));
