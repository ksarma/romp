import { test } from "node:test";
import leg from "./real-viewer-leg";
test("p143", (t) => ((leg || null) as any).inBrowser(t, async () => {}));
