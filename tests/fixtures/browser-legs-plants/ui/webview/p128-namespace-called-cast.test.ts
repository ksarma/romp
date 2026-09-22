import { test } from "node:test";
import * as leg from "./real-viewer-leg";
test("p128", async (t) => { await (leg as any)(t, async () => {}); });
