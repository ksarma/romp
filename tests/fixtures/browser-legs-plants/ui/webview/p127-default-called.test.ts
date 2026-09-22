import { test } from "node:test";
import leg from "./real-viewer-leg";
test("p127", async (t) => { await leg(t, async () => {}); });
