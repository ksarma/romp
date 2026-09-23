import { test } from "node:test";
import * as leg from "./real-viewer-leg";
(leg satisfies object).pageHtml();
test("e", (t) => leg.inBrowser(t, async () => {}));
