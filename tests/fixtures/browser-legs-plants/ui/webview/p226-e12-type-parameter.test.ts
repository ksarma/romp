import { test } from "node:test";
import * as leg from "./real-viewer-leg";
function g<leg>(x: leg): leg { return x; } void g;
test("e", (t) => leg.inBrowser(t, async () => {}));
