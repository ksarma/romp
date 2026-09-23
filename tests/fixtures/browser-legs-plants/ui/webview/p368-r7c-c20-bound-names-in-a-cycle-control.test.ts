import { test } from "node:test";
let a = "playwright";
let b = a;
a = b;
test("p368", () => {});
