import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const o: leg.Opened | null = null; void o;
test("e", (t) => leg.inBrowser(t, async () => {}));
