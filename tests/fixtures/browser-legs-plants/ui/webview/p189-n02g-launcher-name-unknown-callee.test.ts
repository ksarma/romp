import { test } from "node:test";
import { load } from "./plain-loader-helper";
const leg = load("./real-viewer-leg");
test("p189", async (t) => { await leg.inBrowser(t, async () => {}); });
