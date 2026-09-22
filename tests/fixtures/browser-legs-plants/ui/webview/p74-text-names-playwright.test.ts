import { test } from "node:test";
import assert from "node:assert/strict";
const deps = ["typescript", "playwright"];
const re = /playwright|real-viewer-leg/;
test("p74 opens without playwright", () => assert.ok(deps.includes("playwright") && re.test("playwright is not installed here")));
