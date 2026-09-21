import { test } from "node:test";
import { launchIt } from "./pw-helper";
test("p34", async () => { const b = await launchIt(); await b.close(); });
