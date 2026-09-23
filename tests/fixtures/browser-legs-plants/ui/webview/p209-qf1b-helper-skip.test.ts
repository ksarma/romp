import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { maybe } from "./skip-helper";
test("p209-own", (t) => inBrowser(t, async () => {}));
test("p209-helper", (t) => maybe(t, async () => {}));
