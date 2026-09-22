import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const alias = leg;
test("p59", async (t) => { await alias.inBrowser(t, async () => {}); });
