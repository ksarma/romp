import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { inBrowser as ib2 } from "./leg-barrel";
test("d1 direct call and a call through the barrel's named re-export", async (t) => { await inBrowser(t, async () => {}); await ib2(t, async () => {}, "firefox"); });
