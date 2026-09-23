import { test } from "node:test";
import * as leg from "./real-viewer-leg";
class H { set leg(v: number) { void v; } } void H;
test("e", (t) => leg.inBrowser(t, async () => {}));
