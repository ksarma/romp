import { test } from "node:test";
import * as leg from "./real-viewer-leg";
class H { x = leg; } void H;
test("e", (t) => leg.inBrowser(t, async () => {}));
