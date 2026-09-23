import { test } from "node:test";
import * as leg from "./real-viewer-leg";
interface Cfg { leg(): void } export type { Cfg };
test("e", (t) => leg.inBrowser(t, async () => {}));
