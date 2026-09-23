import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import { rows } from "./todo-prop-helper";
test("p214-own", (t) => inBrowser(t, async () => {}));
test("p214-helper", () => { void rows([{ id: "a" }]); });
