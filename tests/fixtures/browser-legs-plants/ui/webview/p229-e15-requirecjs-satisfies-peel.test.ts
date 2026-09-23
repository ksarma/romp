import { test } from "node:test";
import { requireCjs, inBrowser } from "./real-viewer-leg";
(requireCjs satisfies Function)("node:path");
test("e15", (t) => inBrowser(t, async () => {}));
