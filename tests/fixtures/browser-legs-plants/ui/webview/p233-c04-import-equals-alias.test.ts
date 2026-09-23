import { test } from "node:test";
import * as leg from "./real-viewer-leg";
import ib = leg.inBrowser;
test("c04", (t) => ib(t, async () => {}));
