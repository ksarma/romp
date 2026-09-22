import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const l = leg && (globalThis as any).other;
test("p144", (t) => l.inBrowser(t, async () => {}));
