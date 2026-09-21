import { test } from "node:test";
import { x } from "./no-such-module";
test("p37", () => x());
