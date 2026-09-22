import { test } from "node:test";
const ff = (process.env.FLAG ? require("playwright") : null).firefox;
test("p104", async () => { const b = await ff.launch(); await b.close(); });
