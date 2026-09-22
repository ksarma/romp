import { test } from "node:test";
import * as realLeg from "./real-viewer-leg";
const leg = process.env.FLAG ? realLeg : null;
test("p111", (t) => leg.inBrowser(t, async () => {}));
