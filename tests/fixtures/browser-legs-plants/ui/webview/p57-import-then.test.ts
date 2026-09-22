import { test } from "node:test";
test("p57", () => import("playwright").then((pw) => pw.chromium.launch()).then((b) => b.close()));
