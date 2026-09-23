import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { inFirefox } from "./chain-helper";
test("p211-own", (t) => inBrowser(t, async () => {}));
test("p211-helper", (t) => inFirefox(t, async () => {}));
