import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
var engine = "chromium";
for (var engine of ["firefox"]) {}
test("p154", (t) => inBrowser(t, async () => {}, engine as any));
