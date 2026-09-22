import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
let engine = "chromium";
for (engine of ["firefox"]) {}
test("p139", (t) => inBrowser(t, async () => {}, engine as any));
