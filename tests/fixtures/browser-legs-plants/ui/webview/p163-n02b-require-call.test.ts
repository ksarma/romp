import { test } from "node:test";
test("p163", async () => { const b = await (require as any).call(null, "playwright").firefox.launch(); await b.close(); });
