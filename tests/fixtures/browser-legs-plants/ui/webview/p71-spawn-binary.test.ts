import { test } from "node:test";
import { spawn } from "node:child_process";
test("p71", () => { const p = spawn("chromium", ["--headless", "about:blank"]); p.kill(); });
