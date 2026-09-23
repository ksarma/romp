import { test } from "node:test";
test("p270", async () => { const b = await require("playwright").firefox.launch(); await b.close(); await import("playwright").then((m) => m.webkit.launch()).then((w) => w.close()); });
