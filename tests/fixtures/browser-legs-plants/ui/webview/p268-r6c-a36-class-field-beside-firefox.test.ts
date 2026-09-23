import { test } from "node:test";
class T { pw = require("playwright"); async run(): Promise<void> { const b = await this.pw.webkit.launch(); await b.close(); } }
test("p268", async () => { const b = await require("playwright").firefox.launch(); await b.close(); await new T().run(); });
