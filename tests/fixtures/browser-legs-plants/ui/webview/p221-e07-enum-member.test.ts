import { test } from "node:test";
import * as leg from "./real-viewer-leg";
enum E { leg } void E;
test("e", (t) => leg.inBrowser(t, async () => {}));
