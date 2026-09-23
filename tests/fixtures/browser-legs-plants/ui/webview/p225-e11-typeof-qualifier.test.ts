import { test } from "node:test";
import * as leg from "./real-viewer-leg";
let f: typeof leg.pageHtml; void f;
test("e", (t) => leg.inBrowser(t, async () => {}));
