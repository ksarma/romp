import { test } from "node:test";
import { inFirefox } from "./ff-helper";
test("p213", (t) => inFirefox(t, async () => {}));
