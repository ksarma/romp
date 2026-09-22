import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { launchIt } from "./requirecjs-helper";
test("p98", (t) => inBrowser(t, async () => { const b = await launchIt(); await b.close(); }));
