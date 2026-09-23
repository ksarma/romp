import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { inBrowser as ib2 } from "./leg-barrel2";
test("d4 direct call and a call through a barrel of the barrel", async (t) => { await inBrowser(t, async () => {}); await ib2(t, async () => {}, "firefox"); });
