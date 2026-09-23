import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { open } from "./leg-barrel-renamed";
test("d2 direct call and a call through the barrel's renamed re-export", async (t) => { await inBrowser(t, async () => {}); await open(t, async () => {}, "firefox"); });
