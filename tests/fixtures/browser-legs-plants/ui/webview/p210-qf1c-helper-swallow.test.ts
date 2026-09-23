import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { safe } from "./swallow-helper";
test("p210-own", (t) => inBrowser(t, async () => {}));
test("p210-helper", (t) => safe(t, async () => {}));
