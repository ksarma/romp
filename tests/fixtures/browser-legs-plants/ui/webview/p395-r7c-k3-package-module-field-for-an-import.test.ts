import { test } from "node:test";
import * as h from "./bundler-pkg-module";
test("p395", async () => { await h.go(); });
