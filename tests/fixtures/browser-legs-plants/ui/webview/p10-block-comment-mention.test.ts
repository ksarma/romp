import { test } from "node:test";
import assert from "node:assert/strict";
/* this module never calls inBrowser( itself */
import { pageHtml } from "./real-viewer-leg";
test("p10", () => assert.ok(pageHtml() === ""));
