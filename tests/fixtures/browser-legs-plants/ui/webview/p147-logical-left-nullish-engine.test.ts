import { test } from "node:test";
import * as leg from "./real-viewer-leg";
test("p147", (t) => (leg ?? null).inBrowser(t, async () => {}, "firefox" as any));
