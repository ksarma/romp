import { test } from "node:test";
function f(require: (s: string) => unknown): void { void require; }
test("p260", () => { f(() => 1); });
