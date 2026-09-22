import { test } from "node:test";
const leg = process.env.FLAG ? require("./real-viewer-leg") : null;
test("p109", (t) => leg.inBrowser(t, async () => {}));
