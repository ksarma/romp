import { test } from "node:test";
import * as leg from "./real-viewer-leg";
(<any>leg).pageHtml();
test("e", (t) => leg.inBrowser(t, async () => {}));
