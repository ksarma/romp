import { test } from "node:test";
async function close(b: Promise<any>): Promise<void> { await (await b).close(); }
test("p276", async () => { await close(require("playwright").firefox.launch()); });
