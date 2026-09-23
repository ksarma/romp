import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const x = (leg satisfies object).inBrowser; void x;
test("e", (t) => leg.inBrowser(t, async () => {}));
