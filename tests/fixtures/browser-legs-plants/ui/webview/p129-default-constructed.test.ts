import { test } from "node:test";
import leg from "./real-viewer-leg";
test("p129", (t) => { const run = new (leg as any)(t); void run; });
