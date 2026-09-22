import { test } from "node:test";
const { firefox } = process.env.FLAG ? require("playwright") : { firefox: null };
test("p103", async () => { const b = await firefox.launch(); await b.close(); });
