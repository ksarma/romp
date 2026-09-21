import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
test("p11", () => assert.ok(fs.readFileSync("real-viewer-leg.ts", "utf8").includes("export async function inBrowser(")));
