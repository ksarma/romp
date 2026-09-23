import { test } from "node:test";
import { createRequire } from "node:module";
import * as path from "node:path";
const load = createRequire(path.join(process.cwd(), "package.json"));
const h = load("../ui/webview/bundler-pkg-main");
test("p399", async () => { await h.go(); });
