import { test } from "node:test";
class T { pw = require("playwright"); async run(): Promise<void> { const b = await this.pw.webkit.launch(); await b.close(); } }
test("p271", async () => { await new T().run(); });
