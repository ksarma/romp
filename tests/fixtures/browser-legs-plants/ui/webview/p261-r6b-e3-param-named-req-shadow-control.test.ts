import { test } from "node:test";
import { createRequire } from "node:module";
const req = createRequire(__filename);
function f(req: (s: string) => unknown): void { void req; }
test("p261", () => { f(() => 1); });
