import { test } from "node:test";
import * as leg from "./real-viewer-leg";
test("p142", (t) => (leg ?? null).inBrowser(t, async () => {}));
