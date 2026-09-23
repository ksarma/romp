import { test } from "node:test";
import { spawnSync } from "node:child_process";
import * as path from "node:path";
test("p234", () => { const r = spawnSync(process.execPath, [path.join(__dirname, "spawn-driver.mjs")], { encoding: "utf8" }); if (r.status !== 0) throw new Error(r.stderr); });
