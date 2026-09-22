import { test } from "node:test";
import { inBrowser, Engine } from "./real-viewer-leg";
async function run(t: any, engine: Engine): Promise<void> { await inBrowser(t, async () => {}, engine); }
test("p76", (t) => run(t, "webkit"));
