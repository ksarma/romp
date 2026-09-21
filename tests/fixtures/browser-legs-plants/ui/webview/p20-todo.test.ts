import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test.todo("p20a", (t) => inBrowser(t, async () => {}));
test("p20b", { todo: true }, (t) => inBrowser(t, async () => {}));
