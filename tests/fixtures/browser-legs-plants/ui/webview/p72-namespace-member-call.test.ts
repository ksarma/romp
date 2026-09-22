import { test } from "node:test";
import * as leg from "./real-viewer-leg";
test("p72", (t) => leg.inBrowser.call(null, t, async () => {}));
