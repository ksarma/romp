import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const bound = leg.inBrowser.bind(null);
test("p73", (t) => bound(t, async () => {}));
