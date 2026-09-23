import { test } from "node:test";
import { fork } from "node:child_process";
test("p235", () => { fork(new URL("./fork-driver.ts", import.meta.url)); });
