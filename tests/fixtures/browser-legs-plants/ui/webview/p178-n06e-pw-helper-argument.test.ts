import { test } from "node:test";
import { launchWith } from "./pw-launch-helper";
const pw = require("playwright");
test("p178", async () => { await launchWith(pw); });
