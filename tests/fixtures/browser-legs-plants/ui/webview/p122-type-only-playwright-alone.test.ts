import { test } from "node:test";
import type { chromium } from "playwright";
test("p122", () => { const k: typeof chromium | null = null; void k; });
