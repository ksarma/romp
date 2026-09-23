import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { inFirefox } from "./ff-helper";
test("p208-own", (t) => inBrowser(t, async () => {}));
test("p208-helper", (t) => inFirefox(t, async () => {}));
