import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const ok = leg !== null;
test("p149", (t) => { void ok; return leg.inBrowser(t, async () => {}); });
