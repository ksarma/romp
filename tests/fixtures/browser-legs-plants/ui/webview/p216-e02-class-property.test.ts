import { test } from "node:test";
import * as leg from "./real-viewer-leg";
class H { leg = 1; } void H;
test("e", (t) => leg.inBrowser(t, async () => {}));
