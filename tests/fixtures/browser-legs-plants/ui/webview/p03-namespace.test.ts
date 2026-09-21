import { test } from "node:test";
import * as leg from "./real-viewer-leg";
test("p3", (t) => leg.inBrowser(t, async () => {}));
