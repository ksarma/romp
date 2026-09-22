import { test } from "node:test";
import * as leg from "./real-viewer-leg";
function which(): string { return process.env.FN as string; }
test("p65", async (t) => { await (leg as any)[which()](t, async () => {}); });
